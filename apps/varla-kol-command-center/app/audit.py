"""Audit-trail service kept separate from SQLite schema mechanics."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db import Database
from app.schemas import AuditRecord


class AuditTrail:
    """Append immutable operator and system actions to durable storage."""

    def __init__(self, database: Database):
        self.database = database

    def append(
        self,
        *,
        action: str,
        task_id: str | None = None,
        actor: str = "system",
        details: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> AuditRecord:
        return self.database.append_audit(
            action=action,
            task_id=task_id,
            actor=actor,
            details=details,
            connection=connection,
        )
