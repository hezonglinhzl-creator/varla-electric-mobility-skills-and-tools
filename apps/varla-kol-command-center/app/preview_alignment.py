"""Generate and validate local previews after one manual recognition action."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from app.db import Database


ELIGIBLE_STATES = frozenset(
    {"classified", "needs_knowledge", "manual_review", "previewed"}
)


class PreviewActions(Protocol):
    def generate_preview(self, task_id: str, **options: object) -> object: ...


class PreviewAlignmentService:
    """Align eligible SQLite tasks without owning any Gmail mutation method."""

    def __init__(self, database: Database, actions: PreviewActions) -> None:
        self.database = database
        self.actions = actions

    def align(self, task_ids: Iterable[str] = ()) -> dict[str, int]:
        preferred = list(dict.fromkeys(task_id for task_id in task_ids if task_id))
        connection = self.database._connect()
        try:
            rows = connection.execute(
                "SELECT id, state FROM tasks ORDER BY created_at ASC, id ASC"
            ).fetchall()
        finally:
            connection.close()
        states = {str(row["id"]): str(row["state"]) for row in rows}
        eligible = [
            task_id
            for task_id in preferred
            if states.get(task_id) in ELIGIBLE_STATES
        ]
        eligible.extend(
            task_id
            for task_id, state in states.items()
            if state in ELIGIBLE_STATES and task_id not in eligible
        )
        summary = {
            "eligible": len(eligible),
            "generated": 0,
            "matched": 0,
            "manual_review": 0,
            "needs_knowledge": 0,
            "skipped": sum(state not in ELIGIBLE_STATES for state in states.values()),
            "failed": 0,
        }
        for task_id in eligible:
            try:
                raw = self.actions.generate_preview(task_id)
            except Exception:
                summary["failed"] += 1
                continue
            result = raw if isinstance(raw, Mapping) else {}
            status = result.get("status")
            if status == "previewed":
                summary["generated"] += 1
                summary["matched"] += 1
            elif status == "manual_review":
                summary["generated"] += 1
                summary["manual_review"] += 1
            elif status == "needs_knowledge":
                summary["needs_knowledge"] += 1
            elif status in {"invalid_state", "needs_reclassification"}:
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
        return summary


__all__ = ["ELIGIBLE_STATES", "PreviewAlignmentService"]
