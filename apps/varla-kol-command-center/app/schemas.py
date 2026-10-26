"""Typed persistence records shared by command-center workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


TASK_STATES = (
    "unrecognized",
    "classified",
    "previewed",
    "approved",
    "executing",
    "completed",
    "needs_knowledge",
    "needs_reclassification",
    "manual_review",
    "retryable",
    "ignored",
)

TASK_GROUPS = (
    "kol",
    "pre-sales",
    "order-logistics",
    "after-sales",
    "manual",
)

TaskState = Literal[
    "unrecognized",
    "classified",
    "previewed",
    "approved",
    "executing",
    "completed",
    "needs_knowledge",
    "needs_reclassification",
    "manual_review",
    "retryable",
    "ignored",
]

TaskGroup = Literal[
    "kol",
    "pre-sales",
    "order-logistics",
    "after-sales",
    "manual",
]


class TaskRecord(BaseModel):
    """A durable unit of workflow work.

    ``payload`` is a detached persistence snapshot. Mutating it cannot mutate
    stored JSON; callers must perform an explicit database update to persist
    later changes.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    idempotency_key: str
    state: TaskState
    group: TaskGroup | None = None
    gmail_thread_id: str | None = None
    source_message_id: str | None = None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AuditRecord(BaseModel):
    """An audit event whose details are detached from persisted JSON."""

    model_config = ConfigDict(frozen=True)

    id: int
    task_id: str | None = None
    action: str
    actor: str
    details: dict[str, Any]
    created_at: datetime
