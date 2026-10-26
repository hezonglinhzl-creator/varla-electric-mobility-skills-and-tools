"""Explicit workflow transition policy."""

from __future__ import annotations

from app.schemas import TASK_STATES, TaskState


ALLOWED: dict[str, set[str]] = {
    "unrecognized": {"classified", "ignored"},
    "classified": {"previewed", "ignored"},
    "previewed": {"approved", "ignored"},
    "approved": {"executing"},
    "executing": {
        "completed",
        "needs_knowledge",
        "needs_reclassification",
        "manual_review",
        "retryable",
    },
    "retryable": {"executing", "ignored"},
    "needs_knowledge": {"previewed", "ignored"},
    "needs_reclassification": {"classified", "ignored"},
    "manual_review": {"previewed", "approved", "ignored"},
    "completed": set(),
    "ignored": set(),
}

_documented_states = set(ALLOWED)
_transition_targets = {
    target for targets in ALLOWED.values() for target in targets
}
if _documented_states != set(TASK_STATES) or not _transition_targets <= set(
    TASK_STATES
):
    raise RuntimeError("workflow transitions and typed task states have drifted")


class InvalidTransition(ValueError):
    """Raised when a workflow attempts an undocumented state change."""


def transition(current: str, target: str) -> TaskState:
    """Validate and return a requested workflow state."""
    if target not in ALLOWED.get(current, set()):
        raise InvalidTransition(f"{current} -> {target} is not allowed")
    return target  # type: ignore[return-value]
