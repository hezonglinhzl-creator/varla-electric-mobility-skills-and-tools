"""Deterministic question-to-preview coverage checks for AI-generated drafts."""

from __future__ import annotations

import re
from typing import Final, Iterable

from app.context_alignment import requested_facts
from app.message_text import latest_message_text

_INTENT_PATTERNS: Final[dict[str, tuple[re.Pattern[str], ...]]] = {
    "commission": (
        re.compile(r"\b(?:commission|affiliate|percentage|rate)\b", re.I),
        re.compile(r"佣金|分成"),
    ),
    "contract": (
        re.compile(r"\b(?:contract|agreement|sign(?:ed|ature)?)\b", re.I),
        re.compile(r"合同|协议|签字|签名"),
    ),
    "shipping": (
        re.compile(r"\b(?:ship(?:ping|ment)?|tracking|delivery|carrier)\b", re.I),
        re.compile(r"发货|物流|追踪|到货|快递"),
    ),
    "price": (
        re.compile(r"\b(?:price|cost|discount|coupon|promo)\b", re.I),
        re.compile(r"价格|多少钱|优惠|折扣"),
    ),
    "content_requirements": (
        re.compile(r"\b(?:content requirements?|video brief|deliverables?)\b", re.I),
        re.compile(r"内容要求|视频要求|交付"),
    ),
}
_MODEL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![a-z0-9])(?:varla\s+)?(m5s|m7s)(?![a-z0-9])",
    re.I,
)
_WRAPPER_THEN_GREETING_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*thanks\s+for\s+(?:reaching\s+out|your\s+message)\.\s*"
    r"(?:hi|hello|hey|dear)\b",
    re.I,
)
_GENERIC_OPENING_RE: Final[re.Pattern[str]] = re.compile(
    r"\bthanks\s+for\s+(?:reaching\s+out|your\s+message)\b",
    re.I,
)


def _intents(text: str) -> set[str]:
    found = {
        name
        for name, patterns in _INTENT_PATTERNS.items()
        if any(pattern.search(text) for pattern in patterns)
    }
    found.update(
        f"model:{match.casefold()}" for match in _MODEL_RE.findall(text)
    )
    return found


def _structural_issues(reply: str) -> list[str]:
    if (
        _WRAPPER_THEN_GREETING_RE.search(reply)
        or len(_GENERIC_OPENING_RE.findall(reply)) > 1
    ):
        return ["duplicate_opening"]
    return []


def evaluate_reply_relevance(
    question: str,
    reply: str,
    *,
    provided_facts: Iterable[str] = (),
) -> dict[str, object]:
    """Return a serializable coverage result; it never authorizes an action."""
    requested = _intents(latest_message_text(question))
    answered = _intents(reply)
    missing = sorted(requested - answered)
    guarded = {
        intent
        for intent in answered - requested
        if intent in {"commission", "contract", "shipping"}
        or intent.startswith("model:")
    }
    unsupported = sorted(f"unasked:{intent}" for intent in guarded)
    repeated = sorted(set(provided_facts) & requested_facts(reply))
    structural_issues = _structural_issues(reply)
    issue_count = (
        len(missing) + len(unsupported) + len(repeated) + len(structural_issues)
    )
    denominator = max(1, len(requested) + len(guarded))
    confidence = max(0.0, 1.0 - (issue_count / denominator))
    return {
        "status": "matched" if issue_count == 0 else "manual_review",
        "confidence": round(confidence, 4),
        "requested_intents": sorted(requested),
        "answered_intents": sorted(answered),
        "missing_intents": missing,
        "unsupported_intents": unsupported,
        "repeated_requests": repeated,
        "structural_issues": structural_issues,
    }


__all__ = ["evaluate_reply_relevance"]
