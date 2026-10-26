"""Deterministic policy gates for proposed outbound actions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re
from types import MappingProxyType
from typing import Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, Field, field_validator

from app.classifier import (
    GROUP_ROUTES,
    INTERNAL_DOMAIN,
    RISK_PATTERNS,
    is_internal_sender,
    normalize_text,
    parse_mailbox,
)
from app.schemas import TASK_GROUPS, TaskGroup


AUTO_CONFIDENCE_THRESHOLD = 0.95
PolicyAction = Literal["label", "reply", "forward"]
POLICY_ACTIONS = frozenset({"label", "reply", "forward"})
HIGH_SOURCE_RISK_FLAGS = frozenset(flag for flag, _ in RISK_PATTERNS) | {
    "bulk_marketing",
    "internal_sender",
    "invalid_sender",
    "vendor_promotion",
}
HARD_SOURCE_RISK_FLAGS = frozenset(
    {
        "bulk_marketing",
        "internal_sender",
        "invalid_sender",
        "minor_creator",
        "vendor_promotion",
    }
)
HARD_CONTENT_RISK_FLAGS = frozenset(
    {
        "minor_creator",
        "legal",
        "personal_data",
        "payment_dispute",
        "privacy_request",
        "safety_incident",
    }
)
MEDIUM_SOURCE_RISK_FLAGS = frozenset(
    {
        "medium_risk",
        "paid_partnership",
        "commission",
        "shipping_timeline",
    }
)
RECIPIENT_WHITELIST = frozenset(
    route["department"]
    for route in GROUP_ROUTES.values()
    if route["department"] is not None
)


@dataclass(frozen=True)
class ApprovedTemplate:
    """Trusted exact-body proof registered for a scenario and action."""

    body: str
    sha256: str
    allowed_group_actions: frozenset[tuple[TaskGroup, PolicyAction]]


@dataclass(frozen=True, slots=True)
class TemplateProof:
    """Exact approved-template evidence accepted by ``evaluate_action``."""

    scenario_id: str
    template_id: str
    template_version: str
    template_hash: str


def _approved_template(
    body: str,
    *allowed: tuple[TaskGroup, PolicyAction],
) -> ApprovedTemplate:
    return ApprovedTemplate(
        body=body,
        sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        allowed_group_actions=frozenset(allowed),
    )


APPROVED_TEMPLATE_REGISTRY: Mapping[
    tuple[str, str, str], ApprovedTemplate
] = MappingProxyType({
    (
        "request-information",
        "request-order-number",
        "1",
    ): _approved_template(
        "Thanks for your note. Please share your order number.",
        ("pre-sales", "forward"),
        ("order-logistics", "forward"),
        ("after-sales", "forward"),
    ),
    (
        "kol-standard-reply",
        "kol-standard-reply",
        "1",
    ): _approved_template(
        "Thanks for reaching out. We received your creator profile.",
        ("kol", "reply"),
    ),
    (
        "conversation_acknowledgement",
        "conversation_acknowledgement",
        "1",
    ): _approved_template(
        "Hi there,\n\nThank you for the update. We appreciate you keeping us "
        "posted and would be happy to stay connected.\n\nBest,\nTeam Member\n"
        "Varla Marketing Team",
        ("kol", "reply"),
    ),
    (
        "extra_platform_content",
        "extra_platform_content",
        "1",
    ): _approved_template(
        "Hi there,\n\nYes, you're welcome to include the bike in your TikTok "
        "Live content as additional exposure. Please keep the agreed "
        "deliverables unchanged.\n\nBest,\nTeam Member\nVarla Marketing Team",
        ("kol", "reply"),
    ),
    (
        "contract_document_received",
        "contract_document_received",
        "1",
    ): _approved_template(
        "Hi there,\n\nThank you for sending the document. We have received it "
        "and will review the agreement and submitted information before "
        "confirming the next step. If anything is missing or needs revision, "
        "we will let you know.\n\nBest,\nTeam Member\nVarla Marketing Team",
        ("kol", "reply"),
    ),
    (
        "deliverable_requirements",
        "deliverable_requirements",
        "1",
    ): _approved_template(
        "Hi there,\n\nThank you for sharing your proposal. Our current "
        "collaboration requires at least four videos. This is the "
        "cooperation structure we currently use, and collaboration is a "
        "mutual selection process, so we hope you understand.\n\nIf this "
        "works for you, please let us know and we can continue reviewing "
        "the collaboration.\n\nBest,\nTeam Member\nVarla Marketing Team",
        ("kol", "reply"),
    ),
    (
        "shipping_timeline",
        "shipping_timeline",
        "2",
    ): _approved_template(
        "Hi there,\n\nFor collaboration orders, shipping is usually arranged "
        "within 1-3 days after the collaboration is confirmed. "
        "Once you receive the tracking number, delivery usually takes 3-5 "
        "days, depending on the carrier and destination.\n\nBest,\nTeam Member\n"
        "Varla Marketing Team",
        ("order-logistics", "reply"),
        ("order-logistics", "forward"),
    ),
    (
        "kol-label",
        "kol-label",
        "1",
    ): _approved_template("", ("kol", "label")),
})

SUPPORTED_SCENARIO_ACTIONS: Mapping[
    str, frozenset[tuple[TaskGroup, PolicyAction]]
] = MappingProxyType({
    scenario_id: frozenset(
        pair
        for (registered_scenario, _, _), template in APPROVED_TEMPLATE_REGISTRY.items()
        if registered_scenario == scenario_id
        for pair in template.allowed_group_actions
    )
    for scenario_id, _, _ in APPROVED_TEMPLATE_REGISTRY
})


def approved_template_proof(
    *,
    text: str,
    group: str,
    action: str,
    scenario_id: str,
    template_id: str,
    template_version: str,
) -> TemplateProof | None:
    """Return proof only when an exact registered body and route match.

    Callers cannot register or hash caller-controlled text through this API.
    Any edit, unknown key, or unsupported group/action pair returns no proof.
    """

    if not all(
        isinstance(value, str) and value
        for value in (
            text,
            group,
            action,
            scenario_id,
            template_id,
            template_version,
        )
    ):
        return None
    approved = APPROVED_TEMPLATE_REGISTRY.get(
        (scenario_id, template_id, template_version)
    )
    if (
        approved is None
        or (group, action) not in approved.allowed_group_actions
        or text != approved.body
        or hashlib.sha256(text.encode("utf-8")).hexdigest() != approved.sha256
    ):
        return None
    return TemplateProof(
        scenario_id=scenario_id,
        template_id=template_id,
        template_version=template_version,
        template_hash=approved.sha256,
    )


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


FORBIDDEN_PATTERNS = _compile(
    r"\bguarantee(?:d|s)?\b",
    r"\bdefinitely\b",
    r"\bimmediately\b",
    r"\bconfirmed refund\b",
    r"\bwe will definitely send\b",
    r"\bfree (?:bike|scooter|product)\b",
    r"\bno budget\b",
    r"保证",
    r"一定会",
    r"立即",
)

MEDIUM_RISK_PATTERNS = _compile(
    r"\bestimated (?:shipping|delivery) timeline\b",
    r"\b(?:payment|compensation|discount code|paid partnership|paid deal)\b",
    r"\bcommission\b",
    r"预计(?:发货|送达)时间",
    r"付款",
    r"补偿",
    r"折扣码",
)


class PolicyDecision(BaseModel):
    """Closed policy result consumed by workflow code."""

    outcome: Literal["ALLOW", "REQUIRE_CONFIRM", "BLOCK"]
    reasons: list[str] = Field(default_factory=list)
    permitted_action: Literal[
        "label",
        "reply",
        "forward",
        "preview_and_confirm",
    ] | None = None
    permitted_recipient: str | None = None

    @field_validator("permitted_recipient", mode="before")
    @classmethod
    def canonicalize_permitted_recipient(cls, value: object) -> str | None:
        if value is None:
            return None
        parsed = parse_mailbox(value if isinstance(value, str) else None)
        if parsed is None:
            raise ValueError("permitted_recipient must be one canonical mailbox")
        return parsed


def _matches_any(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _high_risk_reasons(text: str) -> list[str]:
    return [
        flag
        for flag, patterns in RISK_PATTERNS
        if _matches_any(text, patterns)
    ]


def content_risk_reasons(text: str) -> tuple[str, ...]:
    """Return centralized content risks for preview/manual-review decisions."""

    normalized = normalize_text(text if isinstance(text, str) else None)
    reasons = _high_risk_reasons(normalized)
    if _matches_any(normalized, FORBIDDEN_PATTERNS):
        reasons.append("forbidden_language")
    if _matches_any(normalized, MEDIUM_RISK_PATTERNS):
        reasons.append("medium_risk")
    return tuple(dict.fromkeys(reasons))


def _decision(
    outcome: Literal["ALLOW", "REQUIRE_CONFIRM", "BLOCK"],
    reasons: Sequence[str],
    action: str,
    recipient: str | None,
) -> PolicyDecision:
    if outcome == "ALLOW":
        permitted_action: str | None = action
        permitted_recipient = recipient if action in {"reply", "forward"} else None
    elif outcome == "REQUIRE_CONFIRM":
        permitted_action = "preview_and_confirm"
        permitted_recipient = None
    else:
        permitted_action = None
        permitted_recipient = None
    return PolicyDecision(
        outcome=outcome,
        reasons=list(dict.fromkeys(reasons)),
        permitted_action=permitted_action,
        permitted_recipient=permitted_recipient,
    )


def _valid_template_proof(
    *,
    text: str,
    group: str,
    action: str,
    scenario_id: str | None,
    template_id: str | None,
    template_version: str | None,
    template_hash: str | None,
) -> bool:
    if not all(
        isinstance(value, str) and value
        for value in (scenario_id, template_id, template_version, template_hash)
    ):
        return False
    approved = APPROVED_TEMPLATE_REGISTRY.get(
        (scenario_id, template_id, template_version)
    )
    if approved is None or (group, action) not in approved.allowed_group_actions:
        return False
    rendered_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (
        template_hash.casefold() == approved.sha256
        and rendered_hash == approved.sha256
        and text == approved.body
    )


def evaluate_action(
    text: str,
    group: TaskGroup,
    confidence: float,
    auto_mode: bool = False,
    *,
    secondary_group: TaskGroup | None = None,
    latest_sender: str | None = None,
    latest_sender_external: bool | None = None,
    recipient: str | None = None,
    scenario_id: str | None = None,
    template_id: str | None = None,
    template_version: str | None = None,
    template_hash: str | None = None,
    action: PolicyAction = "forward",
    thread_conflict: bool = False,
    duplicate: bool = False,
    stale: bool = False,
    user_confirmed: bool = False,
    exact_preview_confirmed: bool = False,
    operator_override: bool = False,
    source_risk_flags: tuple[str, ...] | list[str] | None = None,
) -> PolicyDecision:
    """Apply blocking guards, risk gates, and auto-send requirements.

    Missing auto-mode context is treated as unverified and therefore cannot
    produce ``ALLOW``. Explicitly unsafe recipients or replay conditions are
    blocked before content risk is considered.
    """

    normalized = normalize_text(text if isinstance(text, str) else None)
    sender_address = parse_mailbox(latest_sender)
    recipient_address = parse_mailbox(recipient)
    blocking: list[str] = []
    if source_risk_flags is None:
        source_flags: tuple[str, ...] = ()
        blocking.append("source_risk_context_missing")
    elif (
        not isinstance(source_risk_flags, (tuple, list))
        or any(
            not isinstance(flag, str) or not flag
            for flag in source_risk_flags
        )
    ):
        source_flags = ()
        blocking.append("invalid_source_risk_flags")
    else:
        source_flags = tuple(dict.fromkeys(source_risk_flags))

    valid_group = group in TASK_GROUPS and group != "manual"
    if not valid_group:
        blocking.append("invalid_group")
    valid_action = action in POLICY_ACTIONS
    if not valid_action:
        blocking.append("invalid_action")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        blocking.append("invalid_confidence")
    elif not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        blocking.append("invalid_confidence")
    if not isinstance(duplicate, bool):
        blocking.append("invalid_duplicate_flag")
    elif duplicate:
        blocking.append("duplicate")
    if not isinstance(stale, bool):
        blocking.append("invalid_stale_flag")
    elif stale:
        blocking.append("stale")
    if not isinstance(text, str):
        blocking.append("invalid_body")
    if not isinstance(auto_mode, bool):
        blocking.append("invalid_auto_mode")
    if latest_sender_external is not None and not isinstance(
        latest_sender_external, bool
    ):
        blocking.append("invalid_sender_context")
    if not isinstance(thread_conflict, bool):
        blocking.append("invalid_thread_conflict_flag")
    elif thread_conflict:
        blocking.extend(["thread_conflict", "needs_reclassification"])
    if not isinstance(user_confirmed, bool) or not isinstance(
        exact_preview_confirmed, bool
    ):
        blocking.append("invalid_confirmation_flag")
    if not isinstance(operator_override, bool):
        blocking.append("invalid_operator_override")

    if latest_sender is None or sender_address is None:
        blocking.append("invalid_sender")
    sender_internal = bool(sender_address) and is_internal_sender(sender_address)
    if sender_internal or latest_sender_external is False:
        blocking.append("internal_sender")

    if secondary_group is not None:
        if (
            secondary_group not in TASK_GROUPS
            or secondary_group in {"kol", "manual"}
            or group != "kol"
        ):
            blocking.append("classification_conflict")
    mixed = secondary_group is not None and "classification_conflict" not in blocking

    if valid_action:
        if action == "label":
            if group != "kol":
                blocking.append("invalid_action_for_group")
            if recipient is not None:
                blocking.append("unexpected_recipient")
        else:
            if recipient is None:
                blocking.append("missing_recipient")
            elif recipient_address is None:
                blocking.append("invalid_recipient")

            if action == "reply":
                if group != "kol":
                    blocking.append("invalid_action_for_group")
                elif recipient_address and recipient_address != sender_address:
                    blocking.append("unsafe_recipient")
            elif action == "forward":
                routed_group = secondary_group if mixed else group
                expected_department = (
                    GROUP_ROUTES[routed_group]["department"]
                    if routed_group in TASK_GROUPS
                    else None
                )
                if expected_department is None:
                    blocking.append("invalid_action_for_group")
                elif recipient_address:
                    if recipient_address not in RECIPIENT_WHITELIST:
                        blocking.append("unsafe_recipient")
                    if recipient_address != expected_department:
                        blocking.append("wrong_department_recipient")

    if sender_internal and recipient_address and recipient_address.endswith(
        f"@{INTERNAL_DOMAIN}"
    ):
        blocking.append("internal_loop")

    content_risks = _high_risk_reasons(normalized)
    forbidden = _matches_any(normalized, FORBIDDEN_PATTERNS)
    if forbidden:
        content_risks.append("forbidden_language")
    high_risk = (
        [flag for flag in content_risks if flag in HARD_CONTENT_RISK_FLAGS]
        if operator_override
        else content_risks
    )
    source_hard_risk = [
        flag for flag in source_flags if flag in HARD_SOURCE_RISK_FLAGS
    ]
    if source_hard_risk:
        high_risk.extend(source_hard_risk)
    if high_risk:
        blocking.extend(high_risk)
        blocking.append("manual_review")

    if blocking:
        return _decision("BLOCK", blocking, action, recipient_address)

    source_confirmation_flags = [
        flag
        for flag in source_flags
        if flag in MEDIUM_SOURCE_RISK_FLAGS
        or flag not in HARD_SOURCE_RISK_FLAGS
    ]
    source_requires_confirmation = bool(source_confirmation_flags)
    medium_risk = (
        _matches_any(normalized, MEDIUM_RISK_PATTERNS)
        or source_requires_confirmation
    )
    if not auto_mode:
        if user_confirmed and exact_preview_confirmed:
            reasons = ["user_confirmed_exact_preview"]
            if medium_risk:
                reasons.insert(0, "medium_risk")
            if source_requires_confirmation:
                reasons.insert(0, "source_risk")
            return _decision("ALLOW", reasons, action, recipient_address)
        reasons = ["manual_confirmation_required"]
        if medium_risk:
            reasons.insert(0, "medium_risk")
        if source_requires_confirmation:
            reasons.insert(0, "source_risk")
        if not user_confirmed:
            reasons.append("user_not_confirmed")
        if not exact_preview_confirmed:
            reasons.append("exact_preview_not_confirmed")
        return _decision("REQUIRE_CONFIRM", reasons, action, recipient_address)

    reasons: list[str] = []
    if confidence < AUTO_CONFIDENCE_THRESHOLD:
        reasons.append("confidence_below_threshold")
    if latest_sender_external is not True and sender_internal:
        reasons.append("latest_sender_not_external")
    if mixed:
        reasons.append("mixed_classification")
    if medium_risk:
        reasons.append("medium_risk")
    if source_requires_confirmation:
        reasons.extend(["source_risk", *source_confirmation_flags])

    scenario_supported = (
        scenario_id in SUPPORTED_SCENARIO_ACTIONS
        and (group, action) in SUPPORTED_SCENARIO_ACTIONS[scenario_id]
    )
    if not scenario_supported:
        reasons.append("unsupported_scenario_action")
    if not _valid_template_proof(
        text=text,
        group=group,
        action=action,
        scenario_id=scenario_id,
        template_id=template_id,
        template_version=template_version,
        template_hash=template_hash,
    ):
        reasons.append("template_proof_invalid")

    if reasons:
        return _decision(
            "REQUIRE_CONFIRM",
            reasons,
            action,
            recipient_address,
        )
    return _decision(
        "ALLOW",
        ["all_auto_guards_passed"],
        action,
        recipient_address,
    )
