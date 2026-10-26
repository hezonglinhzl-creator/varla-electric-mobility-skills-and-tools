from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import uuid
from email.message import EmailMessage
from email.utils import getaddresses
from pathlib import Path
from typing import Any, Callable, Sequence


try:
    from attachment_utils import (
        ATTACHMENT_CONTENT_TYPES,
        DOCX_CONTENT_TYPE,
        MAX_ATTACHMENT_BYTES,
        MAX_ATTACHMENT_COUNT,
        MAX_ATTACHMENTS_TOTAL_BYTES,
        PreparedAttachment,
        SafetyError,
        add_prepared_attachments,
        prepare_attachments,
    )
except ModuleNotFoundError:
    _attachment_utils_path = Path(__file__).with_name("attachment_utils.py")
    _attachment_utils_spec = importlib.util.spec_from_file_location(
        "varla_gmail_attachment_utils", _attachment_utils_path
    )
    if _attachment_utils_spec is None or _attachment_utils_spec.loader is None:
        raise
    _attachment_utils = importlib.util.module_from_spec(_attachment_utils_spec)
    sys.modules[_attachment_utils_spec.name] = _attachment_utils
    _attachment_utils_spec.loader.exec_module(_attachment_utils)
    ATTACHMENT_CONTENT_TYPES = _attachment_utils.ATTACHMENT_CONTENT_TYPES
    DOCX_CONTENT_TYPE = _attachment_utils.DOCX_CONTENT_TYPE
    MAX_ATTACHMENT_BYTES = _attachment_utils.MAX_ATTACHMENT_BYTES
    MAX_ATTACHMENT_COUNT = _attachment_utils.MAX_ATTACHMENT_COUNT
    MAX_ATTACHMENTS_TOTAL_BYTES = _attachment_utils.MAX_ATTACHMENTS_TOTAL_BYTES
    PreparedAttachment = _attachment_utils.PreparedAttachment
    SafetyError = _attachment_utils.SafetyError
    add_prepared_attachments = _attachment_utils.add_prepared_attachments
    prepare_attachments = _attachment_utils.prepare_attachments

try:
    from google.auth.transport.requests import AuthorizedSession, Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ModuleNotFoundError:
    AuthorizedSession = None
    Request = None
    Credentials = None
    InstalledAppFlow = None


SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
GMAIL_ROOT = "https://gmail.googleapis.com/gmail/v1/users/me"
REQUEST_TIMEOUT_SECONDS = 30
MAX_BODY_CHARS = 100_000
MAX_DECODE_BYTES = 400_000
MAX_MIME_DEPTH = 20
MAX_MIME_PARTS = 200
MAX_READ_ATTACHMENTS = 20
INTERNAL_DOMAIN = "varlascooter.com"
FORWARD_RECIPIENTS = {
    "support@varlascooter.com",
    "customer@varlascooter.com",
}
FORWARD_MARKER_HEADER = "X-Varla-KOL-Forwarded-Source"
MAILBOX_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}"
)


class GmailAPIError(RuntimeError):
    """A sanitized Gmail API error suitable for structured CLI output."""

    def __init__(
        self,
        operation: str,
        http_status: int | None = None,
        *,
        uncertain: bool = False,
        gmail_message_id: str | None = None,
    ):
        super().__init__("Gmail API request failed.")
        self.operation = operation
        self.http_status = http_status
        self.uncertain = uncertain
        self.gmail_message_id = gmail_message_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": "gmail_api_error",
            "message": str(self),
            "http_status": self.http_status,
            "operation": self.operation,
        }


def encode_raw(message: EmailMessage) -> str:
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def _safe_attachment_metadata(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-secret attachment metadata from a bounded Gmail MIME tree."""
    results: list[dict[str, Any]] = []
    part_count = 0

    def walk(part: object, depth: int) -> None:
        nonlocal part_count
        if not isinstance(part, dict):
            return
        if depth > MAX_MIME_DEPTH:
            raise SafetyError("message MIME depth exceeds the safe read limit")
        part_count += 1
        if part_count > MAX_MIME_PARTS:
            raise SafetyError("message MIME part count exceeds the safe read limit")
        filename = part.get("filename")
        body = part.get("body")
        if isinstance(filename, str) and filename:
            safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
            mime_type = part.get("mimeType")
            size = body.get("size") if isinstance(body, dict) else None
            if (
                safe_name
                and safe_name not in {".", ".."}
                and isinstance(mime_type, str)
                and mime_type
                and type(size) is int
                and size >= 0
            ):
                if len(results) >= MAX_READ_ATTACHMENTS:
                    raise SafetyError(
                        "message attachment count exceeds the safe read limit"
                    )
                results.append(
                    {
                        "filename": safe_name,
                        "content_type": mime_type,
                        "bytes": size,
                    }
                )
        children = part.get("parts")
        if isinstance(children, list):
            for child in children:
                walk(child, depth + 1)

    walk(payload, 0)
    return results


def _decoded_size(value: str) -> int:
    unpadded = len(value.rstrip("="))
    return max(0, (unpadded * 3) // 4)


def decode_base64url_bounded(value: str) -> tuple[str, bool]:
    estimated_bytes = _decoded_size(value)
    encoded_limit = ((MAX_DECODE_BYTES + 2) // 3) * 4
    clipped = estimated_bytes > MAX_DECODE_BYTES
    bounded_value = value[:encoded_limit] if clipped else value
    if clipped:
        bounded_value = bounded_value[: len(bounded_value) - (len(bounded_value) % 4)]
    padding = "=" * (-len(bounded_value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(bounded_value + padding)
    except (ValueError, TypeError):
        return "", False
    return decoded.decode("utf-8", errors="replace"), clipped


def decode_base64url(value: str) -> str:
    return decode_base64url_bounded(value)[0]


def message_text_bounded(
    payload: dict[str, Any], _depth: int = 0
) -> tuple[str, bool]:
    if not isinstance(payload, dict):
        return "", False
    if _depth >= MAX_MIME_DEPTH:
        return "", True
    mime_type = str(payload.get("mimeType", ""))
    body = payload.get("body")
    body_data = body.get("data") if isinstance(body, dict) else None
    if isinstance(body_data, str) and mime_type == "text/plain":
        return decode_base64url_bounded(body_data)

    parts = payload.get("parts")
    if isinstance(parts, list):
        for part in parts[:100]:
            text, decode_truncated = message_text_bounded(part, _depth + 1)
            if text or decode_truncated:
                return text, decode_truncated

    if isinstance(body_data, str):
        return decode_base64url_bounded(body_data)
    return "", False


def message_text(payload: dict[str, Any]) -> str:
    return message_text_bounded(payload)[0]


def header_values(payload: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    values: dict[str, list[str]] = {}
    errors: list[str] = []
    headers = payload.get("headers", []) if isinstance(payload, dict) else []
    if not isinstance(headers, list):
        return values, ["headers is not a list"]
    for index, header in enumerate(headers[:500]):
        if not isinstance(header, dict):
            errors.append(f"header {index} is malformed")
            continue
        name = header.get("name")
        value = header.get("value")
        if not isinstance(name, str) or not isinstance(value, str):
            errors.append(f"header {index} is malformed")
            continue
        normalized = name.strip().lower()
        if not normalized:
            errors.append(f"header {index} has no name")
            continue
        values.setdefault(normalized, []).append(value)
    if len(headers) > 500:
        errors.append("header list was truncated")
    return values, errors


def headers_map(payload: dict[str, Any]) -> dict[str, str]:
    values, errors = header_values(payload)
    if "header list was truncated" in errors:
        raise SafetyError("Stopped: message exceeds the safe header limit.")
    for protected_name in ("from", "reply-to"):
        if len(values.get(protected_name, [])) > 1:
            raise SafetyError(
                f"Stopped: {protected_name} header appears more than once."
            )
    return {name: entries[-1] for name, entries in values.items() if entries}


def parse_single_mailbox(value: str, *, field: str = "mailbox") -> str:
    if not isinstance(value, str) or not value.strip():
        raise SafetyError(f"Stopped: {field} is empty.")
    if "\r" in value or "\n" in value:
        raise SafetyError(f"Stopped: {field} contains a line break.")
    parsed = getaddresses([value])
    if len(parsed) != 1:
        raise SafetyError(f"Stopped: {field} must contain exactly one mailbox.")
    display_name, address = parsed[0]
    if "@" in display_name:
        raise SafetyError(f"Stopped: {field} has a deceptive display name.")
    canonical = address.strip().lower()
    if not MAILBOX_PATTERN.fullmatch(canonical):
        raise SafetyError(f"Stopped: {field} is not a valid mailbox.")
    return canonical


def parse_address_list(value: str, *, field: str) -> list[str]:
    if not value:
        return []
    if "\r" in value or "\n" in value:
        raise SafetyError(f"Stopped: {field} contains a line break.")
    parsed = getaddresses([value])
    addresses: list[str] = []
    for display_name, address in parsed:
        canonical = address.strip().lower()
        if not MAILBOX_PATTERN.fullmatch(canonical):
            raise SafetyError(f"Stopped: {field} contains an invalid mailbox.")
        # Gmail commonly emits the recipient's own mailbox as its quoted
        # display name, for example:
        #   "info@varlascooter.com" <info@varlascooter.com>
        # That is not deceptive because both values identify the same mailbox.
        # Keep rejecting every mismatched display name containing an address.
        if "@" in display_name and display_name.strip().lower() != canonical:
            raise SafetyError(f"Stopped: {field} has a deceptive display name.")
        addresses.append(canonical)
    return addresses


def parse_forward_recipient(value: str) -> str:
    if not isinstance(value, str) or value not in FORWARD_RECIPIENTS:
        raise SafetyError(
            "Stopped: forward recipient must be one exact lowercase bare "
            "whitelisted mailbox."
        )
    canonical = parse_single_mailbox(value, field="forward recipient")
    if canonical != value:
        raise SafetyError(
            "Stopped: forward recipient must be one exact lowercase bare "
            "whitelisted mailbox."
        )
    return value


def is_internal_mailbox(address: str) -> bool:
    return address.rsplit("@", 1)[-1].casefold() == INTERNAL_DOMAIN


def _first(values: dict[str, list[str]], name: str) -> str:
    entries = values.get(name, [])
    return entries[0] if len(entries) == 1 else ""


def _canonical_header(
    values: dict[str, list[str]],
    name: str,
    *,
    multiple: bool,
    errors: list[str],
) -> str | list[str] | None:
    entries = values.get(name, [])
    if not entries:
        return [] if multiple else None
    if len(entries) != 1:
        errors.append(f"{name} header appears more than once")
        return [] if multiple else None
    try:
        if multiple:
            return parse_address_list(entries[0], field=name)
        return parse_single_mailbox(entries[0], field=name)
    except SafetyError as exc:
        errors.append(str(exc))
        return [] if multiple else None


def _safe_header(value: str, fallback: str = "") -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split()) or fallback


def _truncated_body(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    text, decode_truncated = message_text_bounded(payload)
    original_chars: int | None = len(text)
    truncated = decode_truncated or len(text) > MAX_BODY_CHARS
    if decode_truncated:
        original_chars = None
    returned = text[:MAX_BODY_CHARS]
    return returned, {
        "truncated": truncated,
        "original_chars": original_chars,
        "returned_chars": len(returned),
        "limit_chars": MAX_BODY_CHARS,
    }


def load_body(args: argparse.Namespace) -> str:
    if args.body_file:
        body = args.body_file.expanduser().resolve().read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        raise ValueError("Provide --body or --body-file.")
    if "\\n" in body or "\\r\\n" in body:
        raise SafetyError(
            "Stopped: visible literal newline markers found in email body. "
            "Use real UTF-8 line breaks in the body file."
        )
    return body


def _expected_sha256(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SafetyError(f"Stopped: {field} must be a lowercase SHA-256 digest.")
    return value


def prepare_locked_compose_inputs(
    args: argparse.Namespace,
) -> tuple[str, list[PreparedAttachment]]:
    """Read once, verify the exact in-memory bytes, then return send inputs."""
    body_sha = _expected_sha256(
        getattr(args, "expected_body_sha256", None),
        field="expected body SHA-256",
    )
    body_bytes = getattr(args, "expected_body_bytes", None)
    if (body_sha is None) != (body_bytes is None):
        raise SafetyError("Stopped: body hash and byte guards must be supplied together.")
    if body_bytes is not None and body_bytes < 0:
        raise SafetyError("Stopped: expected body bytes must not be negative.")
    if body_sha is not None:
        if args.body_file is None or args.body is not None:
            raise SafetyError("Stopped: body guards require --body-file.")
        try:
            payload = args.body_file.expanduser().resolve(strict=True).read_bytes()
        except OSError as exc:
            raise SafetyError("Stopped: body file cannot be read.") from exc
        if len(payload) != body_bytes or hashlib.sha256(payload).hexdigest() != body_sha:
            raise SafetyError("Stopped: body file does not match the approved content.")
        try:
            body = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafetyError("Stopped: body file must be valid UTF-8.") from exc
        if "\\n" in body or "\\r\\n" in body:
            raise SafetyError(
                "Stopped: visible literal newline markers found in email body. "
                "Use real UTF-8 line breaks in the body file."
            )
    else:
        body = load_body(args)

    prepared = prepare_attachments(args.attachment)
    expected_hashes = list(getattr(args, "expected_attachment_sha256", []))
    expected_bytes = list(getattr(args, "expected_attachment_bytes", []))
    if bool(expected_hashes) != bool(expected_bytes):
        raise SafetyError(
            "Stopped: attachment hash and byte guards must be supplied together."
        )
    if expected_hashes or expected_bytes:
        if len(expected_hashes) != len(args.attachment) or len(expected_bytes) != len(
            args.attachment
        ):
            raise SafetyError("Stopped: attachment guard count does not match attachments.")
        for index, (item, expected_hash, expected_size) in enumerate(
            zip(prepared, expected_hashes, expected_bytes, strict=True), start=1
        ):
            digest = _expected_sha256(
                expected_hash,
                field=f"expected attachment {index} SHA-256",
            )
            if expected_size < 0:
                raise SafetyError(
                    "Stopped: expected attachment bytes must not be negative."
                )
            if (
                item.metadata["sha256"] != digest
                or item.metadata["bytes"] != expected_size
            ):
                raise SafetyError(
                    f"Stopped: attachment {index} does not match the approved content."
                )
    return body, prepared


def _validate_mode(mode: str, confirm: str | None) -> None:
    if mode not in {"draft", "send"}:
        raise SafetyError("Stopped: mode must be draft or send.")
    if mode == "send" and confirm != "SEND":
        raise SafetyError(
            "Real sending requires both --mode send and --confirm SEND."
        )


def default_send_audit_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        root = Path(local_app_data)
    else:
        root = Path.home() / "AppData" / "Local"
    return root / "VarlaKOLCommandCenter" / "gmail-send-audit.sqlite3"


class SendAuditStore:
    """Lease-based send state without message content."""

    def __init__(
        self,
        path: Path | str,
        *,
        clock: Callable[[], datetime] | None = None,
        lease_seconds: int = 120,
    ):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lease_seconds = lease_seconds

    @staticmethod
    def idempotency_hash(
        account: str,
        thread_id: str,
        source_message_id: str,
        action: str,
    ) -> str:
        material = "\0".join(
            [account, thread_id, source_message_id, action]
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def stable_message_id(idempotency_hash: str) -> str:
        return f"<varla-kol-{idempotency_hash}@varlascooter.com>"

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        connection.row_factory = sqlite3.Row
        self._ensure_schema(connection)
        return connection

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS send_audit (
                account TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                source_message_id TEXT NOT NULL,
                action TEXT NOT NULL,
                idempotency_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_id TEXT NOT NULL,
                lease_until TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                gmail_message_id TEXT,
                stable_message_id TEXT NOT NULL,
                reconciliation_check_count INTEGER NOT NULL DEFAULT 0,
                last_checked_at TEXT,
                negative_observation INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (
                    account,
                    thread_id,
                    source_message_id,
                    action
                )
            ) WITHOUT ROWID
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(send_audit)")
        }
        migrations = {
            "status": "TEXT",
            "attempt_id": "TEXT",
            "lease_until": "TEXT",
            "gmail_message_id": "TEXT",
            "stable_message_id": "TEXT",
            "reconciliation_check_count": "INTEGER DEFAULT 0",
            "last_checked_at": "TEXT",
            "negative_observation": "INTEGER DEFAULT 0",
        }
        for name, data_type in migrations.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE send_audit ADD COLUMN {name} {data_type}"
                )
        rows = connection.execute(
            """
            SELECT account, thread_id, source_message_id, action,
                   idempotency_hash, status, attempt_id, lease_until,
                   stable_message_id, reconciliation_check_count,
                   negative_observation
            FROM send_audit
            """
        ).fetchall()
        for row in rows:
            key = row["idempotency_hash"] or self.idempotency_hash(
                row["account"],
                row["thread_id"],
                row["source_message_id"],
                row["action"],
            )
            connection.execute(
                """
                UPDATE send_audit
                SET idempotency_hash = ?,
                    status = COALESCE(status, 'unknown'),
                    attempt_id = COALESCE(attempt_id, ''),
                    lease_until = COALESCE(lease_until, ''),
                    stable_message_id = COALESCE(stable_message_id, ?),
                    reconciliation_check_count =
                        COALESCE(reconciliation_check_count, 0),
                    negative_observation = COALESCE(negative_observation, 0)
                WHERE account = ? AND thread_id = ?
                  AND source_message_id = ? AND action = ?
                """,
                (
                    key,
                    self.stable_message_id(key),
                    row["account"],
                    row["thread_id"],
                    row["source_message_id"],
                    row["action"],
                ),
            )
        connection.commit()

    @staticmethod
    def _row_result(row: sqlite3.Row, **overrides: Any) -> dict[str, Any]:
        result = dict(row)
        result.update(overrides)
        return result

    def claim(
        self,
        *,
        account: str,
        thread_id: str,
        source_message_id: str,
        action: str,
    ) -> dict[str, Any]:
        key = self.idempotency_hash(
            account,
            thread_id,
            source_message_id,
            action,
        )
        stable_id = self.stable_message_id(key)
        now = self._now()
        lease_until = now + timedelta(seconds=self.lease_seconds)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT * FROM send_audit
                    WHERE account = ? AND thread_id = ?
                      AND source_message_id = ? AND action = ?
                    """,
                    (account, thread_id, source_message_id, action),
                ).fetchone()
                if row is None:
                    attempt_id = uuid.uuid4().hex
                    connection.execute(
                        """
                        INSERT INTO send_audit (
                            account, thread_id, source_message_id, action,
                            idempotency_hash, status, attempt_id, lease_until,
                            timestamp, gmail_message_id, stable_message_id,
                            reconciliation_check_count, last_checked_at,
                            negative_observation
                        ) VALUES (
                            ?, ?, ?, ?, ?, 'pending', ?, ?, ?, NULL, ?,
                            0, NULL, 0
                        )
                        """,
                        (
                            account,
                            thread_id,
                            source_message_id,
                            action,
                            key,
                            attempt_id,
                            lease_until.isoformat(),
                            now.isoformat(),
                            stable_id,
                        ),
                    )
                    connection.commit()
                    return {
                        "status": "claimed",
                        "attempt_id": attempt_id,
                        "idempotency_hash": key,
                        "stable_message_id": stable_id,
                    }

                status = row["status"] or "unknown"
                stored_lease = row["lease_until"] or ""
                lease_active = False
                if stored_lease:
                    try:
                        lease_active = (
                            datetime.fromisoformat(stored_lease) > now
                        )
                    except ValueError:
                        lease_active = False

                if status == "sent":
                    connection.commit()
                    return self._row_result(
                        row,
                        status="already_processed",
                        reason="sent",
                    )
                if status == "unknown":
                    connection.commit()
                    return self._row_result(
                        row,
                        status="needs_reconciliation",
                        audit_status="unknown",
                    )
                if status == "in_progress":
                    if lease_active:
                        connection.commit()
                        return self._row_result(
                            row,
                            status="already_processed",
                            reason="in_progress",
                        )
                    connection.execute(
                        """
                        UPDATE send_audit
                        SET status = 'unknown', lease_until = '', timestamp = ?
                        WHERE account = ? AND thread_id = ?
                          AND source_message_id = ? AND action = ?
                        """,
                        (
                            now.isoformat(),
                            account,
                            thread_id,
                            source_message_id,
                            action,
                        ),
                    )
                    connection.commit()
                    return self._row_result(
                        row,
                        status="needs_reconciliation",
                        audit_status="unknown",
                    )
                if status == "pending" and lease_active:
                    connection.commit()
                    return self._row_result(
                        row,
                        status="already_processed",
                        reason="pending",
                    )

                attempt_id = uuid.uuid4().hex
                connection.execute(
                    """
                    UPDATE send_audit
                    SET status = 'pending', attempt_id = ?, lease_until = ?,
                        timestamp = ?, gmail_message_id = NULL,
                        idempotency_hash = ?, stable_message_id = ?,
                        reconciliation_check_count = 0,
                        last_checked_at = NULL, negative_observation = 0
                    WHERE account = ? AND thread_id = ?
                      AND source_message_id = ? AND action = ?
                    """,
                    (
                        attempt_id,
                        lease_until.isoformat(),
                        now.isoformat(),
                        key,
                        stable_id,
                        account,
                        thread_id,
                        source_message_id,
                        action,
                    ),
                )
                connection.commit()
                return {
                    "status": "claimed",
                    "attempt_id": attempt_id,
                    "idempotency_hash": key,
                    "stable_message_id": stable_id,
                }
        except sqlite3.Error:
            raise SafetyError(
                "Stopped: local send audit could not be written safely."
            ) from None

    def begin_attempt(self, attempt_id: str) -> None:
        now = self._now()
        lease_until = now + timedelta(seconds=self.lease_seconds)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE send_audit
                    SET status = 'in_progress', lease_until = ?, timestamp = ?
                    WHERE attempt_id = ? AND status = 'pending'
                    """,
                    (lease_until.isoformat(), now.isoformat(), attempt_id),
                )
                connection.commit()
                if cursor.rowcount != 1:
                    raise SafetyError(
                        "Stopped: send claim is no longer available."
                    )
        except sqlite3.Error:
            raise SafetyError(
                "Stopped: local send audit could not start safely."
            ) from None

    def _finish_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        gmail_message_id: str | None = None,
    ) -> None:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE send_audit
                    SET status = ?, lease_until = '', timestamp = ?,
                        gmail_message_id = ?
                    WHERE attempt_id = ? AND status = 'in_progress'
                    """,
                    (
                        status,
                        self._now().isoformat(),
                        gmail_message_id,
                        attempt_id,
                    ),
                )
                connection.commit()
                if cursor.rowcount != 1:
                    raise SafetyError(
                        "Stopped: send audit state changed unexpectedly."
                    )
        except sqlite3.Error:
            raise SafetyError(
                "Stopped: local send audit could not be finalized safely."
            ) from None

    def mark_sent(self, attempt_id: str, gmail_message_id: str) -> None:
        self._finish_attempt(
            attempt_id,
            status="sent",
            gmail_message_id=gmail_message_id,
        )

    def mark_failed(self, attempt_id: str) -> None:
        self._finish_attempt(attempt_id, status="failed")

    def mark_unknown(self, attempt_id: str) -> None:
        self._finish_attempt(attempt_id, status="unknown")

    def get(
        self,
        *,
        account: str,
        thread_id: str,
        source_message_id: str,
        action: str,
    ) -> dict[str, Any] | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT * FROM send_audit
                    WHERE account = ? AND thread_id = ?
                      AND source_message_id = ? AND action = ?
                    """,
                    (account, thread_id, source_message_id, action),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error:
            raise SafetyError(
                "Stopped: local send audit could not be read safely."
            ) from None

    def lease_active(self, record: dict[str, Any]) -> bool:
        lease_until = record.get("lease_until")
        if not isinstance(lease_until, str) or not lease_until:
            return False
        try:
            return datetime.fromisoformat(lease_until) > self._now()
        except ValueError:
            return False

    def reconcile(
        self,
        *,
        account: str,
        thread_id: str,
        source_message_id: str,
        action: str,
        sent: bool,
        gmail_message_id: str | None = None,
        confirm_not_sent: bool = False,
    ) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT reconciliation_check_count FROM send_audit
                    WHERE account = ? AND thread_id = ?
                      AND source_message_id = ? AND action = ?
                    """,
                    (account, thread_id, source_message_id, action),
                ).fetchone()
                if row is None:
                    raise SafetyError(
                        "Stopped: send audit record disappeared."
                    )
                check_count = int(row["reconciliation_check_count"] or 0)
                status = (
                    "sent"
                    if sent
                    else "failed"
                    if confirm_not_sent and check_count >= 1
                    else "unknown"
                )
                connection.execute(
                    """
                    UPDATE send_audit
                        SET status = ?, lease_until = '', timestamp = ?,
                        gmail_message_id = ?,
                        reconciliation_check_count = ?,
                        last_checked_at = ?,
                        negative_observation = ?
                    WHERE account = ? AND thread_id = ?
                      AND source_message_id = ? AND action = ?
                    """,
                    (
                        status,
                        self._now().isoformat(),
                        gmail_message_id,
                        check_count + (0 if sent else 1),
                        self._now().isoformat(),
                        0 if sent else 1,
                        account,
                        thread_id,
                        source_message_id,
                        action,
                    ),
                )
                connection.commit()
            result = self.get(
                account=account,
                thread_id=thread_id,
                source_message_id=source_message_id,
                action=action,
            )
            return result or {}
        except sqlite3.Error:
            raise SafetyError(
                "Stopped: local send audit reconciliation failed."
            ) from None


class GmailClient:
    """Gmail operations over an injected AuthorizedSession-compatible object."""

    def __init__(
        self,
        session: Any,
        *,
        expected_account: str,
        audit_store: SendAuditStore | None = None,
    ):
        self.session = session
        self.expected_account = parse_single_mailbox(
            expected_account, field="expected account"
        )
        self.audit_store = audit_store or SendAuditStore(default_send_audit_path())

    def _request(
        self,
        method: str,
        path: str,
        *,
        operation: str,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"timeout": REQUEST_TIMEOUT_SECONDS}
        if params is not None:
            kwargs["params"] = params
        if json_payload is not None:
            kwargs["json"] = json_payload
        try:
            request_method = getattr(self.session, method.lower())
            response = request_method(f"{GMAIL_ROOT}{path}", **kwargs)
            status = getattr(response, "status_code", None)
            if isinstance(status, int) and status >= 400:
                gmail_message_id = None
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        message_data = error_data.get("message")
                        candidate = (
                            message_data.get("id")
                            if isinstance(message_data, dict)
                            else error_data.get("id")
                        )
                        if isinstance(candidate, str) and candidate:
                            gmail_message_id = candidate
                except Exception:
                    pass
                raise GmailAPIError(
                    operation,
                    status,
                    gmail_message_id=gmail_message_id,
                )
            response.raise_for_status()
            if status == 204:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}
        except GmailAPIError:
            raise
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            raise GmailAPIError(
                operation,
                status,
                uncertain=status is None,
            ) from None

    def verify_account(self) -> str:
        profile = self._request("GET", "/profile", operation="verify account")
        raw_account = profile.get("emailAddress", "")
        try:
            account = parse_single_mailbox(raw_account, field="authenticated account")
        except SafetyError:
            raise SafetyError("Stopped: Gmail did not return a valid account.") from None
        if account != self.expected_account:
            raise SafetyError(
                f"Stopped: authenticated account is {account}, "
                f"expected {self.expected_account}."
            )
        return account

    def get_message(
        self, message_id: str, message_format: str = "full"
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/messages/{message_id}",
            operation="read message",
            params={"format": message_format},
        )

    def list_labels(self) -> list[dict[str, str | None]]:
        data = self._request("GET", "/labels", operation="list labels")
        labels = []
        for item in data.get("labels", [])[:1000]:
            if not isinstance(item, dict):
                continue
            labels.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                }
            )
        return labels

    def read_thread(self, thread_id: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/threads/{thread_id}",
            operation="read thread",
            params={"format": "full"},
        )
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            messages = []
        ordered = sorted(
            (item for item in messages if isinstance(item, dict)),
            key=lambda item: int(item.get("internalDate") or 0),
        )
        formatted = [self._format_thread_message(item) for item in ordered[:1000]]
        latest_external = None
        for item in formatted:
            if item["from"] and not is_internal_mailbox(item["from"]):
                latest_external = item["message_id"]
        return {
            "account": self.expected_account,
            "thread_id": data.get("id") or thread_id,
            "message_count": len(formatted),
            "latest_external_message_id": latest_external,
            "messages": formatted,
            "messages_truncated": len(ordered) > 1000,
        }

    def _format_thread_message(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = data.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        values, errors = header_values(payload)
        body, truncation = _truncated_body(payload)
        return {
            "message_id": data.get("id"),
            "thread_id": data.get("threadId"),
            "internal_date": data.get("internalDate"),
            "internalDate": data.get("internalDate"),
            "from": _canonical_header(
                values, "from", multiple=False, errors=errors
            ),
            "to": _canonical_header(values, "to", multiple=True, errors=errors),
            "cc": _canonical_header(values, "cc", multiple=True, errors=errors),
            "bcc": _canonical_header(values, "bcc", multiple=True, errors=errors),
            "reply_to": _canonical_header(
                values, "reply-to", multiple=False, errors=errors
            ),
            "subject": _safe_header(_first(values, "subject")),
            "date": _safe_header(_first(values, "date")),
            "body": body,
            "body_truncation": truncation,
            "label_ids": [
                value for value in data.get("labelIds", []) if isinstance(value, str)
            ],
            "labelIds": [
                value for value in data.get("labelIds", []) if isinstance(value, str)
            ],
            "header_errors": errors,
            "attachments": _safe_attachment_metadata(payload),
        }

    def add_label(self, thread_id: str, label: str) -> dict[str, Any]:
        if not isinstance(label, str) or label.casefold() != "kol":
            raise SafetyError("Stopped: the first version only allows the KOL label.")
        matches = [
            item
            for item in self.list_labels()
            if isinstance(item.get("name"), str)
            and item["name"].casefold() == "kol"
            and isinstance(item.get("id"), str)
        ]
        if len(matches) != 1:
            raise SafetyError(
                "Stopped: one existing KOL label is required; no label was created."
            )
        selected = matches[0]
        thread = self._request(
            "GET",
            f"/threads/{thread_id}",
            operation="inspect thread labels",
            params={"format": "minimal"},
        )
        messages = [
            item
            for item in thread.get("messages", [])
            if isinstance(item, dict)
        ]
        if messages and all(
            selected["id"] in item.get("labelIds", []) for item in messages
        ):
            return {
                "status": "already_present",
                "thread_id": thread_id,
                "label_id": selected["id"],
                "label": selected["name"],
            }
        self.verify_account()
        self._request(
            "POST",
            f"/threads/{thread_id}/modify",
            operation="add KOL label",
            json_payload={"addLabelIds": [selected["id"]]},
        )
        return {
            "status": "label_added",
            "thread_id": thread_id,
            "label_id": selected["id"],
            "label": selected["name"],
        }

    def mark_spam(
        self,
        thread_id: str,
        source_message_id: str,
        expected_sender: str,
        *,
        confirm: str | None,
    ) -> dict[str, Any]:
        """Move one fully guarded vendor thread to Spam and verify Gmail state."""

        if confirm != "SPAM":
            raise SafetyError("Stopped: moving to Spam requires --confirm SPAM.")
        for value, field in (
            (thread_id, "thread ID"),
            (source_message_id, "source message ID"),
        ):
            if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
                raise SafetyError(f"Stopped: {field} must be a non-empty single-line value.")
        sender = parse_single_mailbox(expected_sender, field="expected sender")
        if is_internal_mailbox(sender):
            raise SafetyError("Stopped: internal Varla mail cannot be moved to Spam.")

        thread = self.read_thread(thread_id)
        messages = thread.get("messages", [])
        messages = [item for item in messages if isinstance(item, dict)]
        matching = [
            item for item in messages if item.get("message_id") == source_message_id
        ]
        if len(matching) != 1:
            raise SafetyError("Stopped: the exact source message is not in this thread.")
        source_sender = parse_single_mailbox(
            matching[0].get("from"), field="source sender"
        )
        if source_sender != sender:
            raise SafetyError("Stopped: the source sender no longer matches.")
        if thread.get("latest_external_message_id") != source_message_id:
            raise SafetyError("Stopped: a newer external message exists in this thread.")
        latest = messages[-1] if messages else None
        if latest is None:
            raise SafetyError("Stopped: the Gmail thread is empty.")
        if latest.get("message_id") != source_message_id:
            latest_sender = parse_single_mailbox(
                latest.get("from"), field="latest thread sender"
            )
            if is_internal_mailbox(latest_sender):
                raise SafetyError(
                    "Stopped: a Varla teammate replied after the vendor message."
                )
            raise SafetyError("Stopped: the source message is no longer latest.")

        self.verify_account()
        already_spam = all(
            "SPAM" in item.get("label_ids", [])
            and "INBOX" not in item.get("label_ids", [])
            for item in messages
        )
        if not already_spam:
            self._request(
                "POST",
                f"/threads/{thread_id}/modify",
                operation="move guarded vendor thread to spam",
                json_payload={
                    "addLabelIds": ["SPAM"],
                    "removeLabelIds": ["INBOX"],
                },
            )
            verified = self.read_thread(thread_id)
            verified_messages = [
                item
                for item in verified.get("messages", [])
                if isinstance(item, dict)
            ]
            if not verified_messages or not all(
                "SPAM" in item.get("label_ids", [])
                and "INBOX" not in item.get("label_ids", [])
                for item in verified_messages
            ):
                raise SafetyError(
                    "Stopped: Gmail did not verify the requested Spam state."
                )

        return {
            "status": "already_spam" if already_spam else "spam_moved",
            "account": self.expected_account,
            "thread_id": thread_id,
            "source_message_id": source_message_id,
            "sender": sender,
            "verified": True,
        }

    def move_to_trash(
        self,
        thread_id: str,
        source_message_id: str,
        expected_sender: str,
        *,
        confirm: str | None,
    ) -> dict[str, Any]:
        """Move one fully guarded vendor thread to recoverable Trash."""

        if confirm != "TRASH":
            raise SafetyError("Stopped: moving to Trash requires --confirm TRASH.")
        for value, field in (
            (thread_id, "thread ID"),
            (source_message_id, "source message ID"),
        ):
            if not isinstance(value, str) or not value or "\r" in value or "\n" in value:
                raise SafetyError(f"Stopped: {field} must be a non-empty single-line value.")
        sender = parse_single_mailbox(expected_sender, field="expected sender")
        if is_internal_mailbox(sender):
            raise SafetyError("Stopped: internal Varla mail cannot be moved to Trash.")

        thread = self.read_thread(thread_id)
        messages = [
            item for item in thread.get("messages", []) if isinstance(item, dict)
        ]
        matching = [
            item for item in messages if item.get("message_id") == source_message_id
        ]
        if len(matching) != 1:
            raise SafetyError("Stopped: the exact source message is not in this thread.")
        source_sender = parse_single_mailbox(
            matching[0].get("from"), field="source sender"
        )
        if source_sender != sender:
            raise SafetyError("Stopped: the source sender no longer matches.")
        if thread.get("latest_external_message_id") != source_message_id:
            raise SafetyError("Stopped: a newer external message exists in this thread.")
        latest = messages[-1] if messages else None
        if latest is None:
            raise SafetyError("Stopped: the Gmail thread is empty.")
        if latest.get("message_id") != source_message_id:
            latest_sender = parse_single_mailbox(
                latest.get("from"), field="latest thread sender"
            )
            if is_internal_mailbox(latest_sender):
                raise SafetyError(
                    "Stopped: a Varla teammate replied after the vendor message."
                )
            raise SafetyError("Stopped: the source message is no longer latest.")

        self.verify_account()
        already_trash = all(
            "TRASH" in item.get("label_ids", [])
            and "INBOX" not in item.get("label_ids", [])
            for item in messages
        )
        if not already_trash:
            self._request(
                "POST",
                f"/threads/{thread_id}/trash",
                operation="move guarded vendor thread to trash",
            )
            verified = self.read_thread(thread_id)
            verified_messages = [
                item
                for item in verified.get("messages", [])
                if isinstance(item, dict)
            ]
            if not verified_messages or not all(
                "TRASH" in item.get("label_ids", [])
                and "INBOX" not in item.get("label_ids", [])
                for item in verified_messages
            ):
                raise SafetyError(
                    "Stopped: Gmail did not verify the requested Trash state."
                )

        return {
            "status": "already_trash" if already_trash else "trash_moved",
            "account": self.expected_account,
            "thread_id": thread_id,
            "source_message_id": source_message_id,
            "sender": sender,
            "verified": True,
        }

    def ensure_sender_trash_filter(
        self,
        expected_sender: str,
        *,
        confirm: str | None,
    ) -> dict[str, Any]:
        """Create one exact-sender Gmail filter that routes future mail to Trash."""

        if confirm != "BLOCK":
            raise SafetyError("Stopped: creating a sender filter requires --confirm BLOCK.")
        sender = parse_single_mailbox(expected_sender, field="expected sender")
        if is_internal_mailbox(sender):
            raise SafetyError("Stopped: internal Varla mail cannot be blocked.")
        self.verify_account()
        listed = self._request(
            "GET", "/settings/filters", operation="list Gmail filters"
        )
        filters = [
            item for item in listed.get("filter", []) if isinstance(item, dict)
        ]
        for item in filters:
            criteria = item.get("criteria")
            action = item.get("action")
            if (
                isinstance(criteria, dict)
                and criteria.get("from") == sender
                and isinstance(action, dict)
                and "TRASH" in action.get("addLabelIds", [])
                and isinstance(item.get("id"), str)
            ):
                return {
                    "status": "filter_exists",
                    "account": self.expected_account,
                    "sender": sender,
                    "filter_id": item["id"],
                    "verified": True,
                }
        payload = {
            "criteria": {"from": sender},
            "action": {"addLabelIds": ["TRASH"]},
        }
        created = self._request(
            "POST",
            "/settings/filters",
            operation="create exact sender Trash filter",
            json_payload=payload,
        )
        filter_id = created.get("id")
        if not isinstance(filter_id, str) or not filter_id:
            raise SafetyError("Stopped: Gmail did not return a filter ID.")
        verified = self._request(
            "GET",
            f"/settings/filters/{filter_id}",
            operation="verify exact sender Trash filter",
        )
        if verified.get("criteria") != payload["criteria"] or verified.get(
            "action"
        ) != payload["action"]:
            raise SafetyError("Stopped: Gmail did not verify the sender filter.")
        return {
            "status": "filter_created",
            "account": self.expected_account,
            "sender": sender,
            "filter_id": filter_id,
            "verified": True,
        }

    def _deliver(
        self,
        message: EmailMessage,
        *,
        mode: str,
        confirm: str | None,
        thread_id: str | None = None,
        idempotency: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        _validate_mode(mode, confirm)
        self.verify_account()
        audit_metadata: dict[str, str] = {}
        if mode == "send":
            claim: dict[str, Any] | None = None
            if idempotency:
                claim = self.audit_store.claim(
                    account=self.expected_account,
                    thread_id=idempotency["thread_id"],
                    source_message_id=idempotency["source_message_id"],
                    action=idempotency["action"],
                )
                if claim["status"] != "claimed":
                    result = {
                        "status": claim["status"],
                        "thread_id": idempotency["thread_id"],
                        "source_message_id": idempotency["source_message_id"],
                        "action": idempotency["action"],
                        "idempotency_hash": claim["idempotency_hash"],
                        "stable_message_id": claim["stable_message_id"],
                    }
                    for name in (
                        "reason",
                        "audit_status",
                        "attempt_id",
                        "gmail_message_id",
                    ):
                        if claim.get(name):
                            result[name] = claim[name]
                    return result
                stable_id = claim["stable_message_id"]
                if message.get("Message-ID"):
                    message.replace_header("Message-ID", stable_id)
                else:
                    message["Message-ID"] = stable_id
                self.audit_store.begin_attempt(claim["attempt_id"])
                audit_metadata = {
                    "source_message_id": idempotency["source_message_id"],
                    "action": idempotency["action"],
                    "idempotency_hash": claim["idempotency_hash"],
                    "stable_message_id": stable_id,
                    "attempt_id": claim["attempt_id"],
                }
            payload: dict[str, str] = {"raw": encode_raw(message)}
            if thread_id:
                payload["threadId"] = thread_id
            try:
                result = self._request(
                    "POST",
                    "/messages/send",
                    operation="send message",
                    json_payload=payload,
                )
            except GmailAPIError as exc:
                if claim is None:
                    raise
                definitely_not_sent = (
                    exc.http_status in {400, 401, 403, 404}
                    and not exc.gmail_message_id
                )
                if not definitely_not_sent:
                    self.audit_store.mark_unknown(claim["attempt_id"])
                    return {
                        "status": "needs_reconciliation",
                        "audit_status": "unknown",
                        "thread_id": idempotency["thread_id"],
                        **audit_metadata,
                    }
                self.audit_store.mark_failed(claim["attempt_id"])
                return {
                    "status": "failed",
                    "retryable": True,
                    "http_status": exc.http_status,
                    "thread_id": idempotency["thread_id"],
                    **audit_metadata,
                }
            status = "sent"
            if claim is not None:
                message_result = result.get("message", result)
                gmail_message_id = (
                    message_result.get("id")
                    if isinstance(message_result, dict)
                    else None
                )
                if not isinstance(gmail_message_id, str) or not gmail_message_id:
                    self.audit_store.mark_unknown(claim["attempt_id"])
                    return {
                        "status": "needs_reconciliation",
                        "audit_status": "unknown",
                        "thread_id": idempotency["thread_id"],
                        **audit_metadata,
                    }
                self.audit_store.mark_sent(
                    claim["attempt_id"],
                    gmail_message_id,
                )
        else:
            payload = {"raw": encode_raw(message)}
            if thread_id:
                payload["threadId"] = thread_id
            result = self._request(
                "POST",
                "/drafts",
                operation="create draft",
                json_payload={"message": payload},
            )
            status = "draft_created"
        message_result = result.get("message", result)
        if not isinstance(message_result, dict):
            message_result = {}
        summary = {
            "status": status,
            "draft_id": result.get("id") if mode == "draft" else None,
            "message_id": message_result.get("id"),
            "thread_id": message_result.get("threadId"),
        }
        summary.update(audit_metadata)
        return summary

    def compose(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        mode: str = "draft",
        confirm: str | None = None,
        attachments: Sequence[Path] = (),
        prepared_attachments: Sequence[PreparedAttachment] | None = None,
    ) -> dict[str, Any]:
        _validate_mode(mode, confirm)
        if prepared_attachments is not None and attachments:
            raise SafetyError(
                "Stopped: prepared attachments and attachment paths cannot be combined."
            )
        prepared = (
            list(prepared_attachments)
            if prepared_attachments is not None
            else prepare_attachments(attachments)
        )
        recipient = parse_single_mailbox(to, field="recipient")
        safe_subject = _safe_header(subject)
        message = EmailMessage()
        message["From"] = self.expected_account
        message["To"] = recipient
        message["Subject"] = safe_subject
        message.set_content(body)
        add_prepared_attachments(message, prepared)
        result = self._deliver(message, mode=mode, confirm=confirm)
        result.update(
            {"from": self.expected_account, "to": recipient, "subject": safe_subject}
        )
        if prepared:
            result["attachments"] = [metadata for _, metadata in prepared]
        return result

    def _reply_freshness(
        self,
        *,
        thread_id: str,
        source_message_id: str,
    ) -> dict[str, Any] | None:
        thread = self._request(
            "GET",
            f"/threads/{thread_id}",
            operation="recheck reply thread",
            params={"format": "full"},
        )
        messages = thread.get("messages", [])
        if not isinstance(messages, list):
            messages = []
        ordered = sorted(
            (item for item in messages if isinstance(item, dict)),
            key=lambda item: int(item.get("internalDate") or 0),
        )
        latest_message_id = ordered[-1].get("id") if ordered else None
        source_index = next(
            (
                index
                for index, item in enumerate(ordered)
                if item.get("id") == source_message_id
            ),
            None,
        )
        if source_index is None:
            return {
                "status": "stale",
                "reason": "source_message_missing",
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "latest_message_id": latest_message_id,
            }

        senders: list[str] = []
        for item in ordered:
            payload = item.get("payload")
            payload = payload if isinstance(payload, dict) else {}
            headers = headers_map(payload)
            sender = parse_single_mailbox(
                headers.get("from", ""),
                field="thread message sender",
            )
            senders.append(sender)

        if is_internal_mailbox(senders[source_index]):
            raise SafetyError("Stopped: reply source is internal.")
        for index in range(source_index + 1, len(ordered)):
            if is_internal_mailbox(senders[index]):
                return {
                    "status": "stale",
                    "reason": "internal_reply_after_source",
                    "thread_id": thread_id,
                    "source_message_id": source_message_id,
                    "latest_message_id": latest_message_id,
                }
        latest_external_id = None
        for item, sender in zip(ordered, senders):
            if not is_internal_mailbox(sender):
                latest_external_id = item.get("id")
        if latest_external_id != source_message_id:
            return {
                "status": "stale",
                "reason": "newer_external_message",
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "latest_message_id": latest_message_id,
            }
        return None

    def reconcile_reply(
        self,
        thread_id: str,
        source_message_id: str,
        *,
        confirm_not_sent: str | None = None,
    ) -> dict[str, Any]:
        if confirm_not_sent not in {None, "NOT_SENT"}:
            raise SafetyError(
                "Stopped: manual not-sent confirmation must be exactly NOT_SENT."
            )
        record = self.audit_store.get(
            account=self.expected_account,
            thread_id=thread_id,
            source_message_id=source_message_id,
            action="reply",
        )
        if record is None:
            raise SafetyError("Stopped: no local reply send audit record exists.")
        if record["status"] == "sent":
            return {
                "status": "sent",
                "reconciled": False,
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "gmail_message_id": record.get("gmail_message_id"),
                "idempotency_hash": record["idempotency_hash"],
                "stable_message_id": record["stable_message_id"],
            }
        if (
            record["status"] == "in_progress"
            and self.audit_store.lease_active(record)
        ):
            return {
                "status": "already_processed",
                "reason": "in_progress",
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "attempt_id": record["attempt_id"],
                "idempotency_hash": record["idempotency_hash"],
                "stable_message_id": record["stable_message_id"],
            }
        if record["status"] not in {"unknown", "in_progress"}:
            return {
                "status": record["status"],
                "reconciled": False,
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "retryable": record["status"] == "failed",
                "idempotency_hash": record["idempotency_hash"],
                "stable_message_id": record["stable_message_id"],
            }

        stable_id = record["stable_message_id"]
        search = self._request(
            "GET",
            "/messages",
            operation="reconcile sent message",
            params={
                "q": f"in:sent rfc822msgid:{stable_id}",
                "maxResults": 2,
            },
        )
        thread = self._request(
            "GET",
            f"/threads/{thread_id}",
            operation="reconcile reply thread",
            params={"format": "full"},
        )
        found_message_id = None
        search_messages = search.get("messages", [])
        if isinstance(search_messages, list):
            for item in search_messages[:2]:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    found_message_id = item["id"]
                    break
        thread_messages = thread.get("messages", [])
        if isinstance(thread_messages, list):
            for item in thread_messages[:1000]:
                if not isinstance(item, dict):
                    continue
                payload = item.get("payload")
                payload = payload if isinstance(payload, dict) else {}
                headers = headers_map(payload)
                if _safe_header(headers.get("message-id", "")) == stable_id:
                    if isinstance(item.get("id"), str):
                        found_message_id = item["id"]
                        break
        reconciled = self.audit_store.reconcile(
            account=self.expected_account,
            thread_id=thread_id,
            source_message_id=source_message_id,
            action="reply",
            sent=found_message_id is not None,
            gmail_message_id=found_message_id,
            confirm_not_sent=(
                confirm_not_sent == "NOT_SENT"
                and int(record.get("reconciliation_check_count") or 0) >= 1
            ),
        )
        if found_message_id:
            return {
                "status": "sent",
                "reconciled": True,
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "gmail_message_id": found_message_id,
                "idempotency_hash": reconciled["idempotency_hash"],
                "stable_message_id": stable_id,
            }
        if reconciled["status"] == "failed":
            return {
                "status": "failed",
                "reconciled": True,
                "retryable": True,
                "thread_id": thread_id,
                "source_message_id": source_message_id,
                "idempotency_hash": reconciled["idempotency_hash"],
                "stable_message_id": stable_id,
                "reconciliation_check_count": reconciled[
                    "reconciliation_check_count"
                ],
            }
        return {
            "status": "needs_manual_confirmation",
            "audit_status": "unknown",
            "reconciled": False,
            "retryable": False,
            "thread_id": thread_id,
            "source_message_id": source_message_id,
            "idempotency_hash": reconciled["idempotency_hash"],
            "stable_message_id": stable_id,
            "reconciliation_check_count": reconciled[
                "reconciliation_check_count"
            ],
            "negative_observation": True,
            "last_checked_at": reconciled["last_checked_at"],
        }

    def reply(
        self,
        message_id: str,
        body: str,
        *,
        mode: str = "draft",
        confirm: str | None = None,
        attachments: Sequence[Path] = (),
    ) -> dict[str, Any]:
        _validate_mode(mode, confirm)
        prepared_attachments = prepare_attachments(attachments)
        source = self.get_message(message_id)
        payload = source.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        headers = headers_map(payload)
        source_sender = parse_single_mailbox(
            headers.get("from", ""), field="reply source sender"
        )
        if is_internal_mailbox(source_sender):
            raise SafetyError("Stopped: reply source is internal.")
        recipient_header = headers.get("reply-to") or headers.get("from", "")
        recipient = parse_single_mailbox(recipient_header, field="reply recipient")
        if is_internal_mailbox(recipient):
            raise SafetyError("Stopped: reply recipient is internal.")
        if FORWARD_MARKER_HEADER.lower() in headers:
            raise SafetyError("Stopped: loop marker found on reply source.")
        subject = _safe_header(headers.get("subject", ""), "Message")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        message = EmailMessage()
        message["From"] = self.expected_account
        message["To"] = recipient
        message["Subject"] = subject
        source_rfc_id = _safe_header(headers.get("message-id", ""))
        if source_rfc_id:
            message["In-Reply-To"] = source_rfc_id
            references = _safe_header(headers.get("references", ""))
            message["References"] = f"{references} {source_rfc_id}".strip()
        message.set_content(body)
        thread_id = source.get("threadId")
        if not isinstance(thread_id, str) or not thread_id:
            raise SafetyError("Stopped: reply source has no thread ID.")
        stale = self._reply_freshness(
            thread_id=thread_id,
            source_message_id=str(source.get("id") or message_id),
        )
        if stale:
            return stale
        add_prepared_attachments(message, prepared_attachments)
        result = self._deliver(
            message,
            mode=mode,
            confirm=confirm,
            thread_id=thread_id,
            idempotency={
                "thread_id": thread_id,
                "source_message_id": str(source.get("id") or message_id),
                "action": "reply",
            },
        )
        result.update(
            {
                "from": self.expected_account,
                "to": recipient,
                "subject": subject,
                "reply_to_message_id": source.get("id"),
                "source_thread_id": source.get("threadId"),
            }
        )
        if prepared_attachments and result.get("status") in {"sent", "draft_created"}:
            result["attachments"] = [metadata for _, metadata in prepared_attachments]
        return result

    def forward(
        self,
        message_id: str,
        to: str,
        body: str,
        *,
        mode: str = "draft",
        confirm: str | None = None,
    ) -> dict[str, Any]:
        _validate_mode(mode, confirm)
        recipient = parse_forward_recipient(to)
        source = self.get_message(message_id)
        payload = source.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        headers = headers_map(payload)
        source_sender = parse_single_mailbox(
            headers.get("from", ""), field="source sender"
        )
        if is_internal_mailbox(source_sender):
            raise SafetyError("Stopped: internal messages cannot be forwarded.")
        if FORWARD_MARKER_HEADER.lower() in headers:
            raise SafetyError("Stopped: forward loop marker already exists.")
        original_body, truncation = _truncated_body(payload)
        subject = _safe_header(headers.get("subject", ""), "Message")
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"
        original_to = []
        original_cc = []
        try:
            original_to = parse_address_list(headers.get("to", ""), field="source to")
            original_cc = parse_address_list(headers.get("cc", ""), field="source cc")
        except SafetyError:
            pass
        forwarded_text = "\n".join(
            [
                body,
                "",
                "---------- Forwarded creator message ----------",
                f"From: {source_sender}",
                f"To: {', '.join(original_to)}",
                f"Cc: {', '.join(original_cc)}",
                f"Date: {_safe_header(headers.get('date', ''))}",
                f"Subject: {_safe_header(headers.get('subject', ''))}",
                f"Source Gmail message ID: {source.get('id', '')}",
                f"Source Gmail thread ID: {source.get('threadId', '')}",
                "",
                original_body,
            ]
        )
        message = EmailMessage()
        message["From"] = self.expected_account
        message["To"] = recipient
        message["Subject"] = subject
        message[FORWARD_MARKER_HEADER] = str(source.get("id", ""))
        message.set_content(forwarded_text)
        result = self._deliver(message, mode=mode, confirm=confirm)
        result.update(
            {
                "from": self.expected_account,
                "to": recipient,
                "subject": subject,
                "source_message_id": source.get("id"),
                "source_thread_id": source.get("threadId"),
                "source_rfc_message_id": _safe_header(
                    headers.get("message-id", "")
                ),
                "source_body_truncation": truncation,
            }
        )
        return result


def load_credentials(args: argparse.Namespace) -> Credentials:
    if Credentials is None or Request is None or InstalledAppFlow is None:
        raise SafetyError(
            "Google Gmail dependencies are not installed; install scripts/requirements.txt."
        )
    try:
        credentials: Credentials | None = None
        token_path = args.token.expanduser().resolve()
        credentials_path = args.credentials.expanduser().resolve()

        if token_path.is_file():
            credentials = Credentials.from_authorized_user_file(token_path, SCOPES)

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        if not credentials or not credentials.valid:
            if not credentials_path.is_file():
                raise SafetyError("OAuth Desktop client JSON not found.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                SCOPES,
            )
            previous_relax_scope = os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE")
            os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
            try:
                credentials = flow.run_local_server(
                    # Chrome extensions can block localhost callbacks before the
                    # loopback listener receives them.  Google desktop OAuth
                    # supports numeric loopback addresses, which avoids that
                    # browser-side interception while remaining local-only.
                    host="127.0.0.1",
                    port=args.oauth_port,
                    open_browser=not args.manual_browser,
                    authorization_prompt_message=(
                        "Open this URL in the Chrome profile for "
                        f"{args.expected_account}: {{url}}"
                    ),
                    success_message=(
                        "Gmail authorization succeeded. You may close this page."
                    ),
                    login_hint=args.expected_account,
                )
            finally:
                if previous_relax_scope is None:
                    os.environ.pop("OAUTHLIB_RELAX_TOKEN_SCOPE", None)
                else:
                    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = previous_relax_scope

            granted_scopes = set(credentials.scopes or ())
            missing_scopes = set(SCOPES) - granted_scopes
            if missing_scopes:
                raise SafetyError(
                    "OAuth authorization did not grant every required Gmail scope."
                )

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return credentials
    except SafetyError:
        raise
    except Exception as exc:
        raise SafetyError(
            "Stopped: OAuth credentials could not be loaded, refreshed, or saved "
            f"({type(exc).__name__})."
        ) from None


def api_client(
    args: argparse.Namespace,
    *,
    session_factory: Callable[[Credentials], Any] | None = None,
) -> GmailClient:
    if session_factory is None:
        if AuthorizedSession is None:
            raise SafetyError(
                "Google Gmail dependencies are not installed; install scripts/requirements.txt."
            )
        session_factory = AuthorizedSession
    client = GmailClient(
        session_factory(load_credentials(args)),
        expected_account=args.expected_account,
    )
    client.verify_account()
    return client


def api_session(args: argparse.Namespace) -> tuple[Any, str]:
    client = api_client(args)
    return client.session, client.expected_account


def output(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def command_authorize(args: argparse.Namespace) -> None:
    client = api_client(args)
    output(
        {
            "status": "authorized",
            "account": client.expected_account,
            "scopes": SCOPES,
        }
    )


def command_verify(args: argparse.Namespace) -> None:
    client = api_client(args)
    client._request(
        "GET",
        "/messages",
        operation="mail read test",
        params={"maxResults": 1, "includeSpamTrash": "false"},
    )
    output(
        {
            "status": "ok",
            "account": client.expected_account,
            "mail_read_test": "passed",
        }
    )


def command_search(args: argparse.Namespace) -> None:
    client = api_client(args)
    data = client._request(
        "GET",
        "/messages",
        operation="search messages",
        params={"q": args.query, "maxResults": args.max_results},
    )
    results = []
    for item in data.get("messages", [])[: args.max_results]:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        detail = client.get_message(item["id"], "metadata")
        headers = headers_map(detail.get("payload", {}))
        results.append(
            {
                "message_id": detail.get("id"),
                "thread_id": detail.get("threadId"),
                "from": headers.get("from"),
                "to": headers.get("to"),
                "subject": headers.get("subject"),
                "date": headers.get("date"),
                "snippet": detail.get("snippet"),
                "label_ids": detail.get("labelIds", []),
            }
        )
    output(
        {
            "account": client.expected_account,
            "query": args.query,
            "messages": results,
        }
    )


def command_read(args: argparse.Namespace) -> None:
    client = api_client(args)
    data = client.get_message(args.message_id)
    formatted = client._format_thread_message(data)
    formatted["account"] = client.expected_account
    output(formatted)


def command_thread_read(args: argparse.Namespace) -> None:
    output(api_client(args).read_thread(args.thread_id))


def command_labels(args: argparse.Namespace) -> None:
    client = api_client(args)
    output({"account": client.expected_account, "labels": client.list_labels()})


def command_label_add(args: argparse.Namespace) -> None:
    output(api_client(args).add_label(args.thread_id, args.label))


def command_spam(args: argparse.Namespace) -> None:
    output(
        api_client(args).mark_spam(
            args.thread_id,
            args.message_id,
            args.sender,
            confirm=args.confirm,
        )
    )


def command_trash(args: argparse.Namespace) -> None:
    output(
        api_client(args).move_to_trash(
            args.thread_id,
            args.message_id,
            args.sender,
            confirm=args.confirm,
        )
    )


def command_filter_block(args: argparse.Namespace) -> None:
    output(
        api_client(args).ensure_sender_trash_filter(
            args.sender,
            confirm=args.confirm,
        )
    )


def command_compose(args: argparse.Namespace) -> None:
    body, prepared = prepare_locked_compose_inputs(args)
    output(
        api_client(args).compose(
            args.to,
            args.subject,
            body,
            mode=args.mode,
            confirm=args.confirm,
            prepared_attachments=prepared,
        )
    )


def command_reply(args: argparse.Namespace) -> None:
    output(
        api_client(args).reply(
            args.message_id,
            load_body(args),
            mode=args.mode,
            confirm=args.confirm,
            attachments=args.attachment,
        )
    )


def command_reply_reconcile(args: argparse.Namespace) -> None:
    output(
        api_client(args).reconcile_reply(
            args.thread_id,
            args.message_id,
            confirm_not_sent=args.confirm_not_sent,
        )
    )


def command_forward(args: argparse.Namespace) -> None:
    output(
        api_client(args).forward(
            args.message_id,
            args.to,
            load_body(args),
            mode=args.mode,
            confirm=args.confirm,
        )
    )


def add_body_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--body")
    group.add_argument("--body-file", type=Path)
    parser.add_argument("--mode", choices=["draft", "send"], default="draft")
    parser.add_argument("--confirm")


def add_attachment_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--attachment", action="append", type=Path, default=[])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Portable, human-controlled Gmail API CLI for Varla KOL email."
    )
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument(
        "--expected-account",
        default="info@varlascooter.com",
    )
    parser.add_argument("--oauth-port", type=int, default=8765)
    parser.add_argument("--manual-browser", action="store_true")

    commands = parser.add_subparsers(dest="command", required=True)
    authorize = commands.add_parser("authorize")
    authorize.set_defaults(handler=command_authorize)
    verify = commands.add_parser("verify")
    verify.set_defaults(handler=command_verify)

    search = commands.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--max-results", type=int, default=10)
    search.set_defaults(handler=command_search)

    read = commands.add_parser("read")
    read.add_argument("--message-id", required=True)
    read.set_defaults(handler=command_read)

    thread_read = commands.add_parser("thread-read")
    thread_read.add_argument("--thread-id", required=True)
    thread_read.set_defaults(handler=command_thread_read)

    labels = commands.add_parser("labels")
    labels.set_defaults(handler=command_labels)

    label_add = commands.add_parser("label-add")
    label_add.add_argument("--thread-id", required=True)
    label_add.add_argument("--label", required=True)
    label_add.set_defaults(handler=command_label_add)

    spam = commands.add_parser("spam")
    spam.add_argument("--thread-id", required=True)
    spam.add_argument("--message-id", required=True)
    spam.add_argument("--sender", required=True)
    spam.add_argument("--confirm", choices=["SPAM"], required=True)
    spam.set_defaults(handler=command_spam)

    trash = commands.add_parser("trash")
    trash.add_argument("--thread-id", required=True)
    trash.add_argument("--message-id", required=True)
    trash.add_argument("--sender", required=True)
    trash.add_argument("--confirm", choices=["TRASH"], required=True)
    trash.set_defaults(handler=command_trash)

    filter_block = commands.add_parser("filter-block")
    filter_block.add_argument("--sender", required=True)
    filter_block.add_argument("--confirm", choices=["BLOCK"], required=True)
    filter_block.set_defaults(handler=command_filter_block)

    compose = commands.add_parser("compose")
    compose.add_argument("--to", required=True)
    compose.add_argument("--subject", required=True)
    add_body_arguments(compose)
    add_attachment_arguments(compose)
    compose.add_argument("--expected-body-sha256")
    compose.add_argument("--expected-body-bytes", type=int)
    compose.add_argument(
        "--expected-attachment-sha256",
        action="append",
        default=[],
    )
    compose.add_argument(
        "--expected-attachment-bytes",
        action="append",
        type=int,
        default=[],
    )
    compose.set_defaults(handler=command_compose)

    reply = commands.add_parser("reply")
    reply.add_argument("--message-id", required=True)
    add_body_arguments(reply)
    add_attachment_arguments(reply)
    reply.set_defaults(handler=command_reply)

    reply_reconcile = commands.add_parser("reply-reconcile")
    reply_reconcile.add_argument("--thread-id", required=True)
    reply_reconcile.add_argument("--message-id", required=True)
    reply_reconcile.add_argument(
        "--confirm-not-sent",
        choices=["NOT_SENT"],
    )
    reply_reconcile.set_defaults(handler=command_reply_reconcile)

    forward = commands.add_parser("forward")
    forward.add_argument("--message-id", required=True)
    forward.add_argument("--to", required=True)
    add_body_arguments(forward)
    forward.set_defaults(handler=command_forward)
    return parser


def main() -> None:
    try:
        args = build_parser().parse_args()
        args.handler(args)
    except GmailAPIError as exc:
        output({"status": "error", "error": exc.as_dict()})
        raise SystemExit(2) from None
    except (SafetyError, ValueError, FileNotFoundError, RuntimeError) as exc:
        output(
            {
                "status": "error",
                "error": {"code": "stopped", "message": str(exc)},
            }
        )
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
