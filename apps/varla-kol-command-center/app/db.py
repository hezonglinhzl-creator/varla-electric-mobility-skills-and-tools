"""SQLite persistence with explicit transaction boundaries."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.redaction import redact_sensitive_json
from app.schemas import (
    TASK_GROUPS,
    TASK_STATES,
    AuditRecord,
    TaskGroup,
    TaskRecord,
    TaskState,
)
from app.state_machine import transition


# Version 3 adds exact-sender blocking for verified vendor promotions.
CURRENT_SCHEMA_VERSION = 3

_BARE_EMAIL_PATTERN = re.compile(
    r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


class UnsupportedSchemaVersion(RuntimeError):
    """Raised when a database cannot safely be opened by this application."""


class TransactionRequiredError(RuntimeError):
    """Raised when a caller connection lacks an explicit active transaction."""


def _sql_choices(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_TASK_STATE_CHOICES = _sql_choices(TASK_STATES)
_TASK_GROUP_CHOICES = _sql_choices(TASK_GROUPS)

OUTBOUND_ACTION_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS outbound_actions (
        id INTEGER PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id),
        action TEXT NOT NULL CHECK (action IN ('reply', 'forward')),
        action_key TEXT NOT NULL UNIQUE,
        owner_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('claimed', 'in_progress', 'sent', 'failed', 'unknown')
        ),
        source_message_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        body_hash TEXT NOT NULL,
        snapshot_updated_at TEXT NOT NULL,
        lease_expires_at TEXT NOT NULL,
        outgoing_message_id TEXT UNIQUE,
        error_code TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_outbound_actions_task_id
    ON outbound_actions(task_id)
    """,
)

BLOCKED_SENDER_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS blocked_senders (
        sender TEXT PRIMARY KEY,
        reason TEXT NOT NULL CHECK (reason = 'vendor_promotion'),
        source_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_blocked_senders_source_task_id
    ON blocked_senders(source_task_id)
    """,
)


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS kol_contacts (
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        display_name TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS kol_cases (
        id INTEGER PRIMARY KEY,
        contact_id INTEGER REFERENCES kol_contacts(id) ON DELETE SET NULL,
        status TEXT NOT NULL,
        summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_kol_cases_contact_id
    ON kol_cases(contact_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS gmail_threads (
        id TEXT PRIMARY KEY,
        last_processed_message_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        idempotency_key TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL CHECK (state IN ({_TASK_STATE_CHOICES})),
        group_name TEXT CHECK (
            group_name IS NULL OR group_name IN ({_TASK_GROUP_CHOICES})
        ),
        gmail_thread_id TEXT REFERENCES gmail_threads(id),
        source_message_id TEXT,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tasks_gmail_thread_id
    ON tasks(gmail_thread_id)
    """,
    f"""
    CREATE TABLE IF NOT EXISTS routing_rules (
        id INTEGER PRIMARY KEY,
        rule_key TEXT NOT NULL UNIQUE,
        group_name TEXT NOT NULL CHECK (group_name IN ({_TASK_GROUP_CHOICES})),
        pattern TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS forward_events (
        id INTEGER PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id),
        action_key TEXT NOT NULL UNIQUE,
        source_message_id TEXT NOT NULL,
        recipient TEXT NOT NULL,
        outgoing_message_id TEXT UNIQUE,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_forward_events_task_id
    ON forward_events(task_id)
    """,
    *OUTBOUND_ACTION_STATEMENTS,
    *BLOCKED_SENDER_STATEMENTS,
    f"""
    CREATE TABLE IF NOT EXISTS knowledge_sources (
        id INTEGER PRIMARY KEY,
        source_key TEXT NOT NULL,
        group_name TEXT NOT NULL CHECK (group_name IN ({_TASK_GROUP_CHOICES})),
        title TEXT NOT NULL,
        version TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (source_key, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_versions (
        id INTEGER PRIMARY KEY,
        skill_name TEXT NOT NULL UNIQUE,
        version TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        details_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_log_task_id
    ON audit_log(task_id)
    """,
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _require_active_transaction(connection: sqlite3.Connection) -> None:
    if not connection.in_transaction:
        raise TransactionRequiredError(
            "caller-supplied SQLite connection must have an active transaction"
        )


class Database:
    """Small SQLite boundary used by workflow services."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection inside an explicit all-or-nothing write transaction."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the durable schema without touching runtime secrets."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, CURRENT_SCHEMA_VERSION):
                raise UnsupportedSchemaVersion(
                    f"database schema version {version} is unsupported; "
                    f"this application supports {CURRENT_SCHEMA_VERSION}"
                )
            existing_tables = {
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    """
                )
            }
            if version == 0 and existing_tables:
                raise UnsupportedSchemaVersion(
                    "unversioned existing database schema is unsupported; "
                    "refusing to assume compatibility"
                )
            if version == 1:
                for statement in OUTBOUND_ACTION_STATEMENTS:
                    connection.execute(statement)
            if version in (1, 2):
                for statement in BLOCKED_SENDER_STATEMENTS:
                    connection.execute(statement)
                connection.execute(
                    f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}"
                )
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            if version == 0:
                connection.execute(
                    f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}"
                )

    def table_names(self) -> list[str]:
        connection = self._connect()
        try:
            return [
                row["name"]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            ]
        finally:
            connection.close()

    def create_task(
        self,
        *,
        idempotency_key: str,
        state: TaskState = "unrecognized",
        group: TaskGroup | None = None,
        gmail_thread_id: str | None = None,
        source_message_id: str | None = None,
        payload: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> TaskRecord:
        """Create a task, joining ``connection`` when supplied.

        Supplying a connection from :meth:`transaction` lets a workflow append
        its audit event in the same atomic unit of work.
        """
        if connection is None:
            with self.transaction() as owned_connection:
                return self.create_task(
                    idempotency_key=idempotency_key,
                    state=state,
                    group=group,
                    gmail_thread_id=gmail_thread_id,
                    source_message_id=source_message_id,
                    payload=payload,
                    connection=owned_connection,
                )

        _require_active_transaction(connection)
        task_id = str(uuid4())
        timestamp = _utc_now()
        payload_json = json.dumps(
            redact_sensitive_json(payload or {}),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        if gmail_thread_id is not None:
            connection.execute(
                """
                INSERT INTO gmail_threads (
                    id, last_processed_message_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_processed_message_id = COALESCE(
                        excluded.last_processed_message_id,
                        gmail_threads.last_processed_message_id
                    ),
                    updated_at = excluded.updated_at
                """,
                (
                    gmail_thread_id,
                    source_message_id,
                    timestamp,
                    timestamp,
                ),
            )
        connection.execute(
            """
            INSERT INTO tasks (
                id, idempotency_key, state, group_name, gmail_thread_id,
                source_message_id, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                idempotency_key,
                state,
                group,
                gmail_thread_id,
                source_message_id,
                payload_json,
                timestamp,
                timestamp,
            ),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return self._task_from_row(row)

    def get_task(self, task_id: str) -> TaskRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else self._task_from_row(row)

    def get_task_by_idempotency_key(
        self, idempotency_key: str
    ) -> TaskRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM tasks WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else self._task_from_row(row)

    def update_task_state(
        self,
        task_id: str,
        target: TaskState,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> TaskRecord:
        """Update state, joining an existing unit of work when supplied."""
        if connection is None:
            with self.transaction() as owned_connection:
                return self.update_task_state(
                    task_id,
                    target,
                    connection=owned_connection,
                )

        _require_active_transaction(connection)
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"task {task_id!r} is missing")

        next_state = transition(row["state"], target)
        connection.execute(
            "UPDATE tasks SET state = ?, updated_at = ? WHERE id = ?",
            (next_state, _utc_now(), task_id),
        )
        updated_row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return self._task_from_row(updated_row)

    def append_audit(
        self,
        *,
        action: str,
        task_id: str | None = None,
        actor: str = "system",
        details: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> AuditRecord:
        """Append an event, joining an existing unit of work when supplied."""
        if connection is None:
            with self.transaction() as owned_connection:
                return self.append_audit(
                    action=action,
                    task_id=task_id,
                    actor=actor,
                    details=details,
                    connection=owned_connection,
                )

        _require_active_transaction(connection)
        timestamp = _utc_now()
        details_json = json.dumps(
            redact_sensitive_json(details or {}),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        cursor = connection.execute(
            """
            INSERT INTO audit_log (
                task_id, action, actor, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, action, actor, details_json, timestamp),
        )
        row = connection.execute(
            "SELECT * FROM audit_log WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return self._audit_from_row(row)

    @staticmethod
    def _normalize_blocked_sender(sender: str) -> str:
        normalized = str(sender).strip().lower()
        if not _BARE_EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("sender must be one valid lowercase bare email address")
        return normalized

    def block_sender(
        self,
        sender: str,
        *,
        reason: str,
        source_task_id: str | None,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        """Persist one exact verified vendor sender without widening the rule."""
        if reason != "vendor_promotion":
            raise ValueError("reason must be vendor_promotion")
        normalized = self._normalize_blocked_sender(sender)
        if connection is None:
            with self.transaction() as owned_connection:
                return self.block_sender(
                    normalized,
                    reason=reason,
                    source_task_id=source_task_id,
                    connection=owned_connection,
                )

        _require_active_transaction(connection)
        timestamp = _utc_now()
        connection.execute(
            """
            INSERT INTO blocked_senders (
                sender, reason, source_task_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(sender) DO UPDATE SET
                reason = excluded.reason,
                source_task_id = COALESCE(
                    excluded.source_task_id,
                    blocked_senders.source_task_id
                ),
                updated_at = excluded.updated_at
            """,
            (normalized, reason, source_task_id, timestamp, timestamp),
        )
        row = connection.execute(
            "SELECT * FROM blocked_senders WHERE sender = ?",
            (normalized,),
        ).fetchone()
        return dict(row)

    def is_sender_blocked(self, sender: str) -> bool:
        normalized = self._normalize_blocked_sender(sender)
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT 1 FROM blocked_senders WHERE sender = ?",
                (normalized,),
            ).fetchone()
        finally:
            connection.close()
        return row is not None

    def list_blocked_senders(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM blocked_senders ORDER BY sender"
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            id=row["id"],
            idempotency_key=row["idempotency_key"],
            state=row["state"],
            group=row["group_name"],
            gmail_thread_id=row["gmail_thread_id"],
            source_message_id=row["source_message_id"],
            payload=json.loads(row["payload_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _audit_from_row(row: sqlite3.Row) -> AuditRecord:
        return AuditRecord(
            id=row["id"],
            task_id=row["task_id"],
            action=row["action"],
            actor=row["actor"],
            details=json.loads(row["details_json"]),
            created_at=row["created_at"],
        )
