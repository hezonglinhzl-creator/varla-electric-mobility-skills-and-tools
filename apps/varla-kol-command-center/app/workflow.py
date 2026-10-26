"""Atomic, human-confirmed Gmail reply and forward workflow."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.classifier import (
    GROUP_ROUTES,
    Classification,
    classify_message,
    is_internal_sender,
    parse_mailbox,
)
from app.db import Database
from app.gmail_gateway import GatewayError, sanitize_error
from app.message_text import latest_message_text
from app.redaction import redact_sensitive_json
from app.risk_policy import (
    PolicyDecision,
    TemplateProof,
    approved_template_proof,
    evaluate_action,
)
from app.state_machine import transition


ACTION_LEASE_SECONDS = 120


class GmailActions(Protocol):
    def thread_read(self, thread_id: str) -> dict[str, Any]: ...

    def reply_send(self, message_id: str, body: str) -> dict[str, Any]: ...

    def forward_send(
        self, message_id: str, recipient: str, body: str
    ) -> dict[str, Any]: ...


class ReplyGenerator(Protocol):
    def generate(
        self,
        message: str,
        group: str,
        classification: object,
        *,
        source_risk_flags: Sequence[str],
        **kwargs: object,
    ) -> object: ...


class WorkflowResult(BaseModel):
    """Stable result returned to API/UI callers."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    action: Literal["reply", "forward"]
    state: str
    status: str
    outgoing_message_id: str | None = None
    recipient: str | None = None
    reasons: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ExecutionSnapshot:
    task_id: str
    action: Literal["reply", "forward"]
    owner_id: str
    task_updated_at: str
    group: str
    thread_id: str
    source_message_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PreparedAction:
    snapshot: ExecutionSnapshot
    body: str
    body_hash: str
    recipient: str
    action_key: str
    decision: PolicyDecision


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _lease_time() -> str:
    return (
        datetime.now(UTC) + timedelta(seconds=ACTION_LEASE_SECONDS)
    ).isoformat(timespec="microseconds")


def _lease_active(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value) > datetime.now(UTC)
    except ValueError:
        return False


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        redact_sensitive_json(dict(value)),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _outgoing_id(result: Mapping[str, Any]) -> str | None:
    for key in ("message_id", "gmail_message_id", "outgoing_message_id"):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _message_order(message: Mapping[str, Any]) -> int:
    value = message.get("internal_date", message.get("internalDate", 0))
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _thread_integrity_reasons(
    thread: Mapping[str, Any],
    *,
    expected_thread_id: str,
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Verify the CLI returned a complete, untruncated canonical thread."""

    reasons: list[str] = []
    if thread.get("thread_id") != expected_thread_id:
        reasons.append("thread_id_mismatch")
    if thread.get("messages_truncated") is not False:
        reasons.append("messages_truncated_not_false")

    raw_messages = thread.get("messages")
    if not isinstance(raw_messages, list):
        return [], [*reasons, "messages_missing"]
    declared_count = thread.get("message_count")
    if (
        not isinstance(declared_count, int)
        or isinstance(declared_count, bool)
        or declared_count != len(raw_messages)
    ):
        reasons.append("message_count_mismatch")

    messages: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_messages):
        prefix = f"message_{index}"
        if not isinstance(item, Mapping):
            reasons.append(f"{prefix}_malformed")
            continue
        messages.append(item)
        message_id = item.get("message_id")
        if not isinstance(message_id, str) or not message_id:
            reasons.append(f"{prefix}_id_missing")
        elif message_id in seen_ids:
            reasons.append(f"{prefix}_id_duplicate")
        else:
            seen_ids.add(message_id)
        if item.get("thread_id") != expected_thread_id:
            reasons.append(f"{prefix}_thread_id_mismatch")
        internal_date = item.get("internalDate")
        try:
            valid_internal_date = (
                isinstance(internal_date, str)
                and bool(internal_date)
                and int(internal_date) >= 0
            )
        except ValueError:
            valid_internal_date = False
        if not valid_internal_date:
            reasons.append(f"{prefix}_internal_date_missing")
        sender = item.get("from")
        sender_address = (
            parse_mailbox(sender) if isinstance(sender, str) else None
        )
        if sender_address is None:
            reasons.append(f"{prefix}_sender_invalid")
        if "reply_to" not in item:
            reasons.append(f"{prefix}_reply_to_evidence_missing")
        else:
            reply_to = item.get("reply_to")
            if reply_to not in {None, ""}:
                reply_address = (
                    parse_mailbox(reply_to)
                    if isinstance(reply_to, str)
                    else None
                )
                if (
                    reply_address is None
                    or is_internal_sender(reply_address)
                    or reply_address != sender_address
                ):
                    reasons.append(f"{prefix}_reply_to_mismatch")
        if not isinstance(item.get("subject"), str):
            reasons.append(f"{prefix}_subject_missing")
        if not isinstance(item.get("body"), str):
            reasons.append(f"{prefix}_body_missing")
        header_errors = item.get("header_errors")
        if not isinstance(header_errors, list):
            reasons.append(f"{prefix}_header_evidence_missing")
        elif header_errors:
            reasons.append(f"{prefix}_header_errors")
        truncation = item.get("body_truncation")
        if (
            not isinstance(truncation, Mapping)
            or truncation.get("truncated") is not False
        ):
            reasons.append(f"{prefix}_body_truncated")
        if item.get("body_truncated", False) is not False:
            reasons.append(f"{prefix}_body_truncated")
    return messages, list(dict.fromkeys(reasons))


def _valid_regenerated_proof(
    regenerated: object,
    *,
    body: str,
    group: str,
    action: str,
) -> bool:
    """Re-issue registry proof and bind it to generated metadata and source."""

    supplied = getattr(regenerated, "proof", None)
    if not isinstance(supplied, TemplateProof):
        return False
    scenario_id = getattr(regenerated, "scenario_id", None)
    template_id = getattr(regenerated, "template_id", None)
    template_version = getattr(regenerated, "template_version", None)
    template_hash = getattr(regenerated, "template_hash", None)
    if not all(
        isinstance(value, str) and value
        for value in (scenario_id, template_id, template_version, template_hash)
    ):
        return False
    reissued = approved_template_proof(
        text=body,
        group=group,
        action=action,
        scenario_id=scenario_id,
        template_id=template_id,
        template_version=template_version,
    )
    if (
        reissued is None
        or supplied != reissued
        or template_hash != reissued.template_hash
        or _body_hash(body) != reissued.template_hash
    ):
        return False
    sources = getattr(regenerated, "sources", None)
    if not isinstance(sources, list):
        return False
    return any(
        getattr(source, "content", None) == body
        and getattr(source, "content_hash", None) == reissued.template_hash
        for source in sources
    )


class ConfirmedWorkflow:
    """Execute one exact, revalidated Gmail action under a SQLite write lock."""

    def __init__(
        self,
        database: Database,
        gmail: GmailActions,
        reply_engine: ReplyGenerator,
        *,
        classifier: Callable[..., Classification] = classify_message,
        policy_evaluator: Callable[..., PolicyDecision] = evaluate_action,
    ) -> None:
        self._database = database
        self._gmail = gmail
        self._reply_engine = reply_engine
        self._classifier = classifier
        self._policy_evaluator = policy_evaluator

    def confirm_reply(self, task_id: str) -> WorkflowResult:
        return self._confirm(task_id, "reply")

    def confirm_forward(self, task_id: str) -> WorkflowResult:
        return self._confirm(task_id, "forward")

    @staticmethod
    def _load_payload(row: sqlite3.Row) -> dict[str, Any]:
        try:
            value = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _existing_result(
        task_id: str,
        action: Literal["reply", "forward"],
        state: str,
        payload: Mapping[str, Any],
    ) -> WorkflowResult | None:
        results = payload.get("action_results")
        results = results if isinstance(results, Mapping) else {}
        stored = results.get(action)
        if not isinstance(stored, Mapping):
            return None
        outgoing = stored.get("outgoing_message_id")
        recipient = stored.get("recipient")
        return WorkflowResult(
            task_id=task_id,
            action=action,
            state=state,
            status="already_completed",
            outgoing_message_id=outgoing if isinstance(outgoing, str) else None,
            recipient=recipient if isinstance(recipient, str) else None,
            reasons=["local_action_result_exists"],
        )

    def _phase_begin(
        self, task_id: str, action: Literal["reply", "forward"]
    ) -> ExecutionSnapshot | WorkflowResult:
        """Claim validation in one short transaction; perform no I/O here."""

        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"task {task_id!r} is missing")
            payload = self._load_payload(row)
            existing_result = self._existing_result(
                task_id, action, str(row["state"]), payload
            )
            if existing_result is not None:
                return existing_result
            durable = connection.execute(
                "SELECT * FROM outbound_actions "
                "WHERE task_id = ? AND action = ? ORDER BY id DESC LIMIT 1",
                (task_id, action),
            ).fetchone()
            if durable is not None:
                durable_status = durable["status"]
                if durable_status == "sent":
                    return WorkflowResult(
                        task_id=task_id,
                        action=action,
                        state="completed",
                        status="already_completed",
                        outgoing_message_id=durable["outgoing_message_id"],
                        recipient=durable["recipient"],
                        reasons=["durable_action_is_sent"],
                    )
                if durable_status == "unknown":
                    if row["state"] == "executing":
                        payload.pop("execution_claim", None)
                        connection.execute(
                            "UPDATE tasks SET state = 'manual_review', "
                            "payload_json = ?, updated_at = ? WHERE id = ?",
                            (
                                _canonical_json(payload),
                                _utc_now(),
                                task_id,
                            ),
                        )
                    return WorkflowResult(
                        task_id=task_id,
                        action=action,
                        state="manual_review",
                        status="needs_reconciliation",
                        recipient=durable["recipient"],
                        reasons=["durable_action_outcome_unknown"],
                    )
                if durable_status in {"claimed", "in_progress"}:
                    if _lease_active(durable["lease_expires_at"]):
                        return WorkflowResult(
                            task_id=task_id,
                            action=action,
                            state=str(row["state"]),
                            status="in_progress",
                            recipient=durable["recipient"],
                            reasons=["durable_action_owner_active"],
                        )
                    connection.execute(
                        "UPDATE outbound_actions SET status = 'unknown', "
                        "error_code = ?, updated_at = ? WHERE id = ?",
                        (
                            "owner_lease_expired",
                            _utc_now(),
                            durable["id"],
                        ),
                    )
                    if row["state"] == "executing":
                        connection.execute(
                            "UPDATE tasks SET state = 'manual_review', "
                            "updated_at = ? WHERE id = ?",
                            (_utc_now(), task_id),
                        )
                    return WorkflowResult(
                        task_id=task_id,
                        action=action,
                        state="manual_review",
                        status="needs_reconciliation",
                        recipient=durable["recipient"],
                        reasons=["durable_action_owner_expired"],
                    )
            claim = payload.get("execution_claim")
            if row["state"] == "executing":
                if (
                    isinstance(claim, Mapping)
                    and claim.get("action") == action
                    and _lease_active(claim.get("lease_expires_at"))
                ):
                    return WorkflowResult(
                        task_id=task_id,
                        action=action,
                        state="executing",
                        status="in_progress",
                        reasons=["validation_owner_active"],
                    )
                connection.execute(
                    "UPDATE tasks SET state = 'manual_review', updated_at = ? "
                    "WHERE id = ?",
                    (_utc_now(), task_id),
                )
                return WorkflowResult(
                    task_id=task_id,
                    action=action,
                    state="manual_review",
                    status="needs_reconciliation",
                    reasons=["validation_owner_missing_or_expired"],
                )
            if payload.get("confirmed_action") != action:
                return WorkflowResult(
                    task_id=task_id,
                    action=action,
                    state=str(row["state"]),
                    status="action_mismatch",
                    reasons=["confirmed_action_does_not_match"],
                )
            if row["state"] not in {"approved", "retryable"}:
                return WorkflowResult(
                    task_id=task_id,
                    action=action,
                    state=str(row["state"]),
                    status="invalid_state",
                    reasons=["task_is_not_approved"],
                )
            thread_id = row["gmail_thread_id"]
            source_message_id = row["source_message_id"]
            group = row["group_name"]
            if not all(
                isinstance(value, str) and value
                for value in (thread_id, source_message_id, group)
            ):
                return WorkflowResult(
                    task_id=task_id,
                    action=action,
                    state=str(row["state"]),
                    status="invalid_source",
                    reasons=["gmail_source_or_group_missing"],
                )
            owner_id = str(uuid4())
            timestamp = _utc_now()
            payload["execution_claim"] = {
                "owner_id": owner_id,
                "action": action,
                "lease_expires_at": _lease_time(),
            }
            connection.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    transition(str(row["state"]), "executing"),
                    _canonical_json(payload),
                    timestamp,
                    task_id,
                ),
            )
            self._database.append_audit(
                task_id=task_id,
                action=f"{action}_validation_claimed",
                actor="user_confirmed_workflow",
                details={"owner_id": owner_id},
                connection=connection,
            )
            return ExecutionSnapshot(
                task_id=task_id,
                action=action,
                owner_id=owner_id,
                task_updated_at=timestamp,
                group=group,
                thread_id=thread_id,
                source_message_id=source_message_id,
                payload=payload,
            )

    def _phase_stop(
        self,
        snapshot: ExecutionSnapshot,
        *,
        target: str,
        status: str,
        reasons: Sequence[object],
        recipient: str | None = None,
    ) -> WorkflowResult:
        """Finalize a pre-send validation result in one short transaction."""

        safe_reasons = [sanitize_error(reason) for reason in reasons]
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (snapshot.task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"task {snapshot.task_id!r} is missing")
            payload = self._load_payload(row)
            claim = payload.get("execution_claim")
            if (
                row["state"] != "executing"
                or not isinstance(claim, Mapping)
                or claim.get("owner_id") != snapshot.owner_id
            ):
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state=str(row["state"]),
                    status="in_progress",
                    reasons=["execution_claim_changed"],
                )
            payload.pop("execution_claim", None)
            events = payload.setdefault("workflow_events", [])
            if isinstance(events, list):
                events.append(
                    {
                        "action": snapshot.action,
                        "status": status,
                        "reasons": safe_reasons,
                        "created_at": _utc_now(),
                    }
                )
            connection.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    transition("executing", target),
                    _canonical_json(payload),
                    _utc_now(),
                    snapshot.task_id,
                ),
            )
            self._database.append_audit(
                task_id=snapshot.task_id,
                action=f"{snapshot.action}_{status}",
                actor="user_confirmed_workflow",
                details={"reasons": safe_reasons, "recipient": recipient},
                connection=connection,
            )
        return WorkflowResult(
            task_id=snapshot.task_id,
            action=snapshot.action,
            state=target,
            status=status,
            recipient=recipient,
            reasons=safe_reasons,
        )

    def _phase_validate(
        self, snapshot: ExecutionSnapshot
    ) -> PreparedAction | WorkflowResult:
        """Perform Gmail read, retrieval, and policy work outside SQLite."""

        try:
            thread = self._gmail.thread_read(snapshot.thread_id)
        except GatewayError as exc:
            return self._phase_stop(
                snapshot,
                target="retryable",
                status="gateway_error",
                reasons=[exc.code, exc.detail],
            )
        messages, integrity_reasons = _thread_integrity_reasons(
            thread, expected_thread_id=snapshot.thread_id
        )
        if integrity_reasons:
            return self._phase_stop(
                snapshot,
                target="needs_reclassification",
                status="stale",
                reasons=integrity_reasons,
            )
        messages.sort(key=_message_order)
        if not messages:
            return self._phase_stop(
                snapshot,
                target="needs_reclassification",
                status="stale",
                reasons=["thread_has_no_messages"],
            )
        latest = messages[-1]
        sender = parse_mailbox(latest.get("from"))
        if sender is None or is_internal_sender(sender):
            return self._phase_stop(
                snapshot,
                target="needs_reclassification",
                status="internal_reply" if sender else "stale",
                reasons=["latest_sender_is_not_external"],
            )
        if (
            latest.get("message_id") != snapshot.source_message_id
            or thread.get("latest_external_message_id")
            != snapshot.source_message_id
        ):
            return self._phase_stop(
                snapshot,
                target="needs_reclassification",
                status="stale",
                reasons=["source_message_changed"],
            )
        body = latest.get("body")
        subject = latest.get("subject")
        if not isinstance(body, str) or not body.strip():
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="needs_knowledge",
                reasons=["source_body_missing"],
            )
        body = latest_message_text(body)
        if not body:
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="needs_knowledge",
                reasons=["current_message_body_missing"],
            )
        context = "\n\n".join(
            str(item.get("body") or "")
            for item in messages[:-1]
            if item.get("body")
        )
        try:
            classification = self._classifier(
                subject=subject,
                body=body,
                thread_context=None,
                latest_sender=sender,
            )
        except Exception:
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="classification_failed",
                reasons=["classifier_failed"],
            )
        primary = classification.primary_group
        secondary = classification.secondary_group
        operator_override = snapshot.payload.get("operator_override") is True
        if snapshot.action == "reply":
            if (
                not operator_override
                and (
                    primary != "kol"
                    or secondary is not None
                    or snapshot.group != "kol"
                )
            ):
                return self._phase_stop(
                    snapshot,
                    target="needs_reclassification",
                    status="classification_changed",
                    reasons=["reply_is_no_longer_pure_kol"],
                )
            retrieval_group = "kol"
            recipient = parse_mailbox(latest.get("reply_to")) or sender
        else:
            retrieval_group = secondary if primary == "kol" else primary
            if retrieval_group not in {
                "pre-sales",
                "order-logistics",
                "after-sales",
            } or snapshot.group not in {primary, retrieval_group}:
                return self._phase_stop(
                    snapshot,
                    target="needs_reclassification",
                    status="classification_changed",
                    reasons=["forward_route_changed"],
                )
            recipient = parse_mailbox(
                GROUP_ROUTES[retrieval_group]["department"]
            )
        if recipient is None:
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="unsafe_recipient",
                reasons=["recipient_not_canonical"],
            )
        stored_source_flags = snapshot.payload.get("source_risk_flags")
        stored_source_flags = (
            [flag for flag in stored_source_flags if isinstance(flag, str)]
            if isinstance(stored_source_flags, list)
            else []
        )
        source_risk_flags = list(
            dict.fromkeys([*classification.risk_flags, *stored_source_flags])
        )
        preview = snapshot.payload.get("preview")
        preview = preview if isinstance(preview, Mapping) else {}
        confirmed_body = preview.get("body")
        confirmed_hash = preview.get("body_sha256")
        edited_by_user = preview.get("edited_by_user") is True
        if (
            not isinstance(confirmed_body, str)
            or not isinstance(confirmed_hash, str)
            or confirmed_hash != _body_hash(confirmed_body)
        ):
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="preview_changed",
                reasons=["exact_confirmed_preview_no_longer_matches"],
                recipient=recipient,
            )
        regenerated = None
        valid_proof = False
        if not operator_override:
            reply_context = classification.model_dump()
            stored_decision = snapshot.payload.get("decision")
            if isinstance(stored_decision, Mapping):
                stored_stage = stored_decision.get("stage_id")
                if isinstance(stored_stage, str) and stored_stage:
                    reply_context["stage_id"] = stored_stage
            reply_context["platform"] = "gmail"
            try:
                regenerated = self._reply_engine.generate(
                    body,
                    retrieval_group,
                    reply_context,
                    source_risk_flags=source_risk_flags,
                    tone=(
                        preview.get("tone")
                        if isinstance(preview.get("tone"), str)
                        else None
                    ),
                    thread_context={
                        "sender": sender,
                        "subject": subject,
                        "platform": "gmail",
                    },
                )
            except Exception:
                return self._phase_stop(
                    snapshot,
                    target="manual_review",
                    status="needs_knowledge",
                    reasons=["scoped_knowledge_generation_failed"],
                    recipient=recipient,
                )
            if getattr(regenerated, "status", None) != "previewed":
                return self._phase_stop(
                    snapshot,
                    target="manual_review",
                    status=str(
                        getattr(regenerated, "status", "needs_knowledge")
                    ),
                    reasons=(
                        getattr(regenerated, "warnings", None)
                        or ["scoped_knowledge_not_approved"]
                    ),
                    recipient=recipient,
                )
            if (
                not edited_by_user
                and getattr(regenerated, "body", None) != confirmed_body
            ):
                return self._phase_stop(
                    snapshot,
                    target="manual_review",
                    status="preview_changed",
                    reasons=["exact_confirmed_preview_no_longer_matches"],
                    recipient=recipient,
                )
            valid_proof = (
                False
                if edited_by_user
                else _valid_regenerated_proof(
                    regenerated,
                    body=confirmed_body,
                    group=primary,
                    action=snapshot.action,
                )
            )
        if (
            source_risk_flags
            and not operator_override
            and (edited_by_user or not valid_proof)
        ):
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="policy_blocked",
                reasons=[
                    (
                        "edited_preview_has_source_risk_flags"
                        if edited_by_user
                        else "action_is_not_low_risk_or_approved"
                    )
                ],
                recipient=recipient,
            )
        decision = self._policy_evaluator(
            confirmed_body,
            "kol" if operator_override and snapshot.action == "reply" else primary,
            classification.confidence,
            auto_mode=False,
            secondary_group=(
                None
                if operator_override and snapshot.action == "reply"
                else secondary
            ),
            latest_sender=sender,
            latest_sender_external=True,
            recipient=recipient,
            scenario_id=(
                None
                if edited_by_user
                else getattr(regenerated, "scenario_id", None)
            ),
            template_id=(
                None
                if edited_by_user
                else getattr(regenerated, "template_id", None)
            ),
            template_version=(
                None
                if edited_by_user
                else getattr(regenerated, "template_version", None)
            ),
            template_hash=(
                None
                if edited_by_user
                else getattr(regenerated, "template_hash", None)
            ),
            action=snapshot.action,
            thread_conflict=False,
            duplicate=False,
            stale=False,
            user_confirmed=True,
            exact_preview_confirmed=True,
            operator_override=operator_override,
            source_risk_flags=source_risk_flags,
        )
        if decision.outcome != "ALLOW":
            return self._phase_stop(
                snapshot,
                target="manual_review",
                status="policy_blocked",
                reasons=decision.reasons,
                recipient=recipient,
            )
        action_key = hashlib.sha256(
            "\x00".join(
                [
                    snapshot.task_id,
                    snapshot.action,
                    snapshot.source_message_id,
                    recipient,
                    confirmed_hash,
                ]
            ).encode("utf-8")
        ).hexdigest()
        return PreparedAction(
            snapshot=snapshot,
            body=confirmed_body,
            body_hash=confirmed_hash,
            recipient=recipient,
            action_key=action_key,
            decision=decision,
        )

    def _phase_claim_action(
        self, prepared: PreparedAction
    ) -> WorkflowResult | None:
        """CAS the task snapshot and durably claim before Gmail mutation."""

        snapshot = prepared.snapshot
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (snapshot.task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"task {snapshot.task_id!r} is missing")
            payload = self._load_payload(row)
            claim = payload.get("execution_claim")
            if (
                row["state"] != "executing"
                or row["updated_at"] != snapshot.task_updated_at
                or not isinstance(claim, Mapping)
                or claim.get("owner_id") != snapshot.owner_id
                or row["gmail_thread_id"] != snapshot.thread_id
                or row["source_message_id"] != snapshot.source_message_id
                or row["group_name"] != snapshot.group
            ):
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state=str(row["state"]),
                    status="stale",
                    recipient=prepared.recipient,
                    reasons=["task_snapshot_changed"],
                )
            current_preview = payload.get("preview")
            if (
                not isinstance(current_preview, Mapping)
                or current_preview.get("body_sha256") != prepared.body_hash
                or current_preview.get("body") != prepared.body
            ):
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state="executing",
                    status="stale",
                    recipient=prepared.recipient,
                    reasons=["confirmed_preview_changed"],
                )
            existing = connection.execute(
                "SELECT * FROM outbound_actions WHERE action_key = ?",
                (prepared.action_key,),
            ).fetchone()
            timestamp = _utc_now()
            lease = _lease_time()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO outbound_actions (
                        task_id, action, action_key, owner_id, status,
                        source_message_id, recipient, body_hash,
                        snapshot_updated_at, lease_expires_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'in_progress', ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.task_id,
                        snapshot.action,
                        prepared.action_key,
                        snapshot.owner_id,
                        snapshot.source_message_id,
                        prepared.recipient,
                        prepared.body_hash,
                        snapshot.task_updated_at,
                        lease,
                        timestamp,
                        timestamp,
                    ),
                )
                return None
            if existing["status"] == "failed":
                connection.execute(
                    """
                    UPDATE outbound_actions
                    SET owner_id = ?, status = 'in_progress',
                        snapshot_updated_at = ?, lease_expires_at = ?,
                        error_code = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.owner_id,
                        snapshot.task_updated_at,
                        lease,
                        timestamp,
                        existing["id"],
                    ),
                )
                return None
            if existing["status"] == "sent":
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state="completed",
                    status="already_completed",
                    outgoing_message_id=existing["outgoing_message_id"],
                    recipient=existing["recipient"],
                    reasons=["durable_action_is_sent"],
                )
            return WorkflowResult(
                task_id=snapshot.task_id,
                action=snapshot.action,
                state="executing",
                status=(
                    "in_progress"
                    if existing["status"] in {"claimed", "in_progress"}
                    and _lease_active(existing["lease_expires_at"])
                    else "needs_reconciliation"
                ),
                recipient=existing["recipient"],
                reasons=["durable_action_not_retryable"],
            )

    def _phase_failure(
        self,
        prepared: PreparedAction,
        *,
        unknown: bool,
        target: str,
        status: str,
        reasons: Sequence[object],
    ) -> WorkflowResult:
        """Finalize a known pre-send failure or an uncertain delivery."""

        snapshot = prepared.snapshot
        safe_reasons = [sanitize_error(reason) for reason in reasons]
        with self._database.transaction() as connection:
            action_row = connection.execute(
                "SELECT * FROM outbound_actions WHERE action_key = ?",
                (prepared.action_key,),
            ).fetchone()
            if (
                action_row is None
                or action_row["owner_id"] != snapshot.owner_id
                or action_row["status"] != "in_progress"
            ):
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state="manual_review",
                    status="needs_reconciliation",
                    recipient=prepared.recipient,
                    reasons=["durable_action_claim_changed"],
                )
            connection.execute(
                "UPDATE outbound_actions SET status = ?, error_code = ?, "
                "updated_at = ? WHERE id = ?",
                (
                    "unknown" if unknown else "failed",
                    safe_reasons[0] if safe_reasons else status,
                    _utc_now(),
                    action_row["id"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (snapshot.task_id,)
            ).fetchone()
            assert row is not None
            payload = self._load_payload(row)
            claim = payload.get("execution_claim")
            if (
                row["state"] == "executing"
                and isinstance(claim, Mapping)
                and claim.get("owner_id") == snapshot.owner_id
            ):
                payload.pop("execution_claim", None)
                connection.execute(
                    "UPDATE tasks SET state = ?, payload_json = ?, "
                    "updated_at = ? WHERE id = ?",
                    (
                        transition("executing", target),
                        _canonical_json(payload),
                        _utc_now(),
                        snapshot.task_id,
                    ),
                )
            self._database.append_audit(
                task_id=snapshot.task_id,
                action=f"{snapshot.action}_{status}",
                actor="user_confirmed_workflow",
                details={"reasons": safe_reasons},
                connection=connection,
            )
        return WorkflowResult(
            task_id=snapshot.task_id,
            action=snapshot.action,
            state=target,
            status=status,
            recipient=prepared.recipient,
            reasons=safe_reasons,
        )

    def _phase_sent(
        self,
        prepared: PreparedAction,
        *,
        gateway_status: str,
        outgoing: str,
    ) -> WorkflowResult:
        """Persist Gmail IDs and completion in one final short transaction."""

        snapshot = prepared.snapshot
        with self._database.transaction() as connection:
            action_row = connection.execute(
                "SELECT * FROM outbound_actions WHERE action_key = ?",
                (prepared.action_key,),
            ).fetchone()
            if (
                action_row is None
                or action_row["owner_id"] != snapshot.owner_id
                or action_row["status"] != "in_progress"
            ):
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state="manual_review",
                    status="needs_reconciliation",
                    recipient=prepared.recipient,
                    reasons=["durable_action_claim_changed_after_send"],
                )
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (snapshot.task_id,)
            ).fetchone()
            assert row is not None
            payload = self._load_payload(row)
            claim = payload.get("execution_claim")
            if (
                row["state"] != "executing"
                or not isinstance(claim, Mapping)
                or claim.get("owner_id") != snapshot.owner_id
            ):
                connection.execute(
                    "UPDATE outbound_actions SET status = 'unknown', "
                    "error_code = ?, updated_at = ? WHERE id = ?",
                    (
                        "task_claim_changed_after_send",
                        _utc_now(),
                        action_row["id"],
                    ),
                )
                return WorkflowResult(
                    task_id=snapshot.task_id,
                    action=snapshot.action,
                    state="manual_review",
                    status="needs_reconciliation",
                    recipient=prepared.recipient,
                    reasons=["task_claim_changed_after_send"],
                )
            connection.execute(
                "UPDATE outbound_actions SET status = 'sent', "
                "outgoing_message_id = ?, updated_at = ? WHERE id = ?",
                (outgoing, _utc_now(), action_row["id"]),
            )
            if snapshot.action == "forward":
                connection.execute(
                    """
                    INSERT INTO forward_events (
                        task_id, action_key, source_message_id, recipient,
                        outgoing_message_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.task_id,
                        prepared.action_key,
                        snapshot.source_message_id,
                        prepared.recipient,
                        outgoing,
                        _utc_now(),
                    ),
                )
            payload.pop("execution_claim", None)
            action_results = payload.setdefault("action_results", {})
            if not isinstance(action_results, dict):
                action_results = {}
                payload["action_results"] = action_results
            action_results[snapshot.action] = {
                "status": "completed",
                "gateway_status": gateway_status,
                "outgoing_message_id": outgoing,
                "recipient": prepared.recipient,
                "source_message_id": snapshot.source_message_id,
                "action_key": prepared.action_key,
                "completed_at": _utc_now(),
            }
            connection.execute(
                "UPDATE tasks SET state = 'completed', payload_json = ?, "
                "updated_at = ? WHERE id = ?",
                (_canonical_json(payload), _utc_now(), snapshot.task_id),
            )
            connection.execute(
                "UPDATE gmail_threads SET last_processed_message_id = ?, "
                "updated_at = ? WHERE id = ?",
                (
                    snapshot.source_message_id,
                    _utc_now(),
                    snapshot.thread_id,
                ),
            )
            self._database.append_audit(
                task_id=snapshot.task_id,
                action=f"{snapshot.action}_completed",
                actor="user_confirmed_workflow",
                details={
                    "outgoing_message_id": outgoing,
                    "recipient": prepared.recipient,
                },
                connection=connection,
            )
        return WorkflowResult(
            task_id=snapshot.task_id,
            action=snapshot.action,
            state="completed",
            status=gateway_status,
            outgoing_message_id=outgoing,
            recipient=prepared.recipient,
            reasons=list(prepared.decision.reasons),
        )

    # External Gmail and AI work occurs between short phase transactions.
    def _confirm(
        self,
        task_id: str,
        action: Literal["reply", "forward"],
    ) -> WorkflowResult:
        begun = self._phase_begin(task_id, action)
        if isinstance(begun, WorkflowResult):
            return begun
        prepared = self._phase_validate(begun)
        if isinstance(prepared, WorkflowResult):
            return prepared
        claimed = self._phase_claim_action(prepared)
        if claimed is not None:
            return claimed
        try:
            if action == "reply":
                gmail_result = self._gmail.reply_send(
                    begun.source_message_id, prepared.body
                )
            else:
                gmail_result = self._gmail.forward_send(
                    begun.source_message_id,
                    prepared.recipient,
                    prepared.body,
                )
        except GatewayError as exc:
            if exc.delivery_unknown:
                return self._phase_failure(
                    prepared,
                    unknown=True,
                    target="manual_review",
                    status="needs_reconciliation",
                    reasons=[exc.code, exc.detail],
                )
            return self._phase_failure(
                prepared,
                unknown=False,
                target="retryable",
                status="gateway_failed",
                reasons=[exc.code, exc.detail],
            )
        except Exception:
            return self._phase_failure(
                prepared,
                unknown=True,
                target="manual_review",
                status="needs_reconciliation",
                reasons=["unexpected_gateway_exception"],
            )
        gateway_status = gmail_result.get("status")
        outgoing = _outgoing_id(gmail_result)
        if gateway_status == "stale":
            return self._phase_failure(
                prepared,
                unknown=False,
                target="needs_reclassification",
                status="stale",
                reasons=[gmail_result.get("reason") or "gateway_stale"],
            )
        if gateway_status == "failed":
            return self._phase_failure(
                prepared,
                unknown=False,
                target="retryable",
                status="gateway_failed",
                reasons=["gmail_action_failed_before_delivery"],
            )
        if (
            gateway_status == "needs_reconciliation"
            or (gateway_status == "already_processed" and outgoing is None)
            or gateway_status not in {"sent", "already_processed"}
            or outgoing is None
        ):
            return self._phase_failure(
                prepared,
                unknown=True,
                target="manual_review",
                status="needs_reconciliation",
                reasons=["gateway_delivery_outcome_unknown"],
            )
        return self._phase_sent(
            prepared,
            gateway_status=str(gateway_status),
            outgoing=outgoing,
        )


__all__ = ["ConfirmedWorkflow", "WorkflowResult"]
