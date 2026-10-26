"""Production composition for the local command center.

All external work still passes through guarded adapters.  Constructing these
services performs local validation/index loading only; Gmail and Feishu are
not contacted until a user invokes an API action.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from app.classifier import (
    GROUP_ROUTES,
    Classification,
    classify_message,
    is_internal_sender,
    parse_mailbox,
)
from app.catalog import LocalCatalog, load_local_catalog
from app.config import AppConfig
from app.context_alignment import analyze_context
from app.db import Database
from app.feishu_sync import FEISHU_WIKI_URL, FeishuSyncer, SyncResult
from app.gmail_gateway import GatewayError, GmailGateway
from app.knowledge import KnowledgeIndex, VALID_GROUPS
from app.message_text import latest_message_text
from app.redaction import redact_sensitive_json
from app.relevance import evaluate_reply_relevance
from app.runtime import resolve_runtime
from app.reply_engine import ReplyEngine
from app.risk_policy import HIGH_SOURCE_RISK_FLAGS, evaluate_action
from app.skill_health import GmailCredentials, SkillHealthChecker
from app.state_machine import InvalidTransition, transition
from app.workflow import ConfirmedWorkflow


AUTO_TRASH_RISK_FLAGS = frozenset({"vendor_promotion"})
MAX_BLOCKED_SENDER_SCAN = 40
JUNK_CLEANUP_QUERY = (
    'in:inbox newer_than:30d {'
    '"guest post" backlink "link building" "seo services" '
    '"link insertion" "shopify expert" "shopify agency" '
    '"ecommerce expert" "e-commerce expert" '
    '"conversion rate optimization" "sales optimization" '
    '"increase sales" "boost sales" "turn into buyers" '
    '"website performing" "not a sales pitch" '
    '"website details" "website traffic" "website inventory" '
    '"website resource library" "publication placement" '
    '"domain authority" "domain rating"}'
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json(value: object) -> str:
    return json.dumps(
        redact_sensitive_json(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        value = json.loads(row["payload_json"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _reply_stage(
    message: str,
    group: str,
    classification: Classification,
    *,
    thread_context: str | None = None,
    creator_context: str | None = None,
) -> str:
    """Choose an approved catalog stage without asking a model to infer it."""
    normalized = message.casefold()
    matched = set(classification.matched_rules)
    alignment = analyze_context(
        message,
        thread_context or "",
        creator_context=creator_context,
    )

    if group == "pre-sales":
        if "pre-sales.purchase_specs" in matched or re.search(
            r"\b(?:specs?|specifications?|motor|range|battery|speed)\b",
            normalized,
        ):
            return "product_specs_question"
        return "presales_service_question"
    if group == "after-sales":
        if re.search(r"\breplacement parts?\b", normalized):
            return "aftersales_service_question"
        if "after-sales.failure_repair" in matched or re.search(
            r"\b(?:broken|brake|repair|damage|not working)\b",
            normalized,
        ):
            return "broken_ebike_evidence_request"
        return "aftersales_service_question"
    if group == "order-logistics":
        return "shipping_timeline"

    history = thread_context.casefold() if isinstance(thread_context, str) else ""
    prior_decline = bool(
        re.search(
            r"(?:not (?:the )?best fit|"
            r"focused on creators who already have a larger|"
            r"partnership spots are limited|"
            r"revisit (?:a |the )?(?:collaboration|conversation)|"
            r"hope to reconnect when the timing is right)",
            history,
        )
    )
    new_performance_evidence = bool(
        re.search(
            r"\b(?:sold|sales|revenue|views?|viewers?|analytics?|"
            r"per month|per day)\b|\$\s*\d",
            normalized,
        )
    )
    closing_acknowledgement = bool(
        re.search(
            r"\b(?:thanks?|thank you).{0,100}"
            r"(?:your time|future|understand|response|opportunity)\b|"
            r"\bhope to collaborate.{0,40}\bfuture\b",
            normalized,
        )
    )
    if prior_decline and new_performance_evidence:
        return "reconsideration_evidence_received"
    if prior_decline and closing_acknowledgement:
        return "decline_acknowledgement"

    if re.search(
        r"\b(?:still need to grow|keep (?:trying|working) to (?:gain|grow)|"
        r"hope(?:fully)? (?:we |i )?can (?:work together|collaborate).{0,30}future)\b",
        normalized,
    ):
        return "decline_acknowledgement"

    if re.search(r"\bm7s\b", normalized) and re.search(
        r"\b(?:commission|affiliate|discount code)\b",
        normalized,
    ):
        return "m7s_commission_multi_intent"
    if (
        "contract_terms" in classification.risk_flags
        and re.search(r"\b(?:document|file|form|attachment|attached)\b", normalized)
    ):
        return "contract_document_received"
    if re.search(r"\b(?:signed|completed|attached)\b.{0,40}\bcontract\b", normalized):
        return "signed_contract_received"
    if re.search(r"\bcontract\b", normalized):
        return "send_contract_form"
    if re.search(
        r"\b(?:tracking|shipment|shipping|delivery|ship)\b|发货|物流|追踪|到货",
        normalized,
    ):
        return "shipping_timeline"
    if re.search(r"\b(?:video brief|content requirements?)\b", normalized):
        return "content_requirements_question"
    deliverable_terms = bool(
        re.search(r"\b(?:videos?|reels?|shorts?|stories|posts?)\b", normalized)
    )
    deliverable_negotiation = bool(
        re.search(
            r"\b(?:too (?:high|many|much)|can (?:only )?do|could (?:only )?do|"
            r"instead|reduce|fewer|only (?:one|two|three|1|2|3))\b",
            normalized,
        )
    )
    if deliverable_terms and deliverable_negotiation:
        return "deliverable_requirements"
    platform_permission = bool(
        re.search(
            r"\b(?:is it (?:okay|ok)|can i|could i|would it be (?:okay|ok)|"
            r"do you mind)\b",
            normalized,
        )
        and re.search(r"\b(?:tiktok|instagram|youtube|facebook)\b", normalized)
        and re.search(r"\b(?:live|stream|show|post|share)\b", normalized)
    )
    if platform_permission:
        return "extra_platform_content"
    if re.search(r"\bdiscount code\b", normalized):
        return "discount_code_question"
    if re.search(r"\b(?:paid collaboration|paid collab|your rate|rates)\b", normalized):
        return "ask_paid_collab"
    if len(normalized) <= 320 and re.search(
        r"\b(?:sounds great|thanks? for (?:the |your )?(?:update|time|response)|"
        r"thank you (?:very much )?for (?:the |your )?(?:update|time|response)|"
        r"appreciate (?:the |your )?(?:update|opportunity)|"
        r"hope(?:fully)? (?:we |i )?can (?:work together|collaborate))\b",
        normalized,
    ):
        return "conversation_acknowledgement"
    has_creator_link = bool(
        {"youtube_link", "tiktok_link", "instagram_link"}
        & set(alignment.provided_facts)
    )
    has_creator_evidence = bool(
        {"audience_information", "performance_metrics"}
        & set(alignment.provided_facts)
    )
    if has_creator_link and has_creator_evidence:
        return "creator_details_received"
    if has_creator_evidence:
        return "ask_missing_creator_links"
    if has_creator_link:
        return "ask_missing_creator_metrics"
    if "kol.product_exchange" in matched:
        return "confirm_product_exchange"
    if re.search(r"\bsponsor(?:ship)?\b", normalized):
        return "ask_sponsorship"
    if "kol.collaboration" in matched or "kol.creator_identity" in matched:
        return "ask_partnership_details"
    return "unknown"


def _decision_envelope(
    message: str,
    classification: Classification,
    *,
    thread_context: str | None = None,
    creator_context: str | None = None,
) -> dict[str, object]:
    """Persist judgment evidence without treating it as action permission."""
    alignment = analyze_context(
        message,
        thread_context or "",
        creator_context=creator_context,
    )
    stage_id = _reply_stage(
        message,
        classification.primary_group,
        classification,
        thread_context=thread_context,
        creator_context=creator_context,
    )
    requires_review = bool(
        classification.risk_flags
        or classification.secondary_group
        or classification.confidence < 0.9
    )
    return {
        "provider": "reply-assistant-policy",
        "version": "1",
        "primary_group": classification.primary_group,
        "secondary_group": classification.secondary_group,
        "stage_id": stage_id,
        "latest_intents": list(alignment.latest_intents),
        "thread_facts": list(alignment.provided_facts),
        "missing_facts": list(alignment.missing_facts),
        "thread_disposition": alignment.disposition,
        "confidence": classification.confidence,
        "evidence": list(classification.matched_rules),
        "requires_manual_review": requires_review,
    }


def _latest_message(thread: Mapping[str, Any]) -> Mapping[str, Any] | None:
    messages = thread.get("messages")
    if not isinstance(messages, list):
        return None
    candidates = [item for item in messages if isinstance(item, Mapping)]
    return max(candidates, key=_message_internal_date, default=None)


def _message_internal_date(item: Mapping[str, Any]) -> int:
    try:
        return int(item.get("internal_date", item.get("internalDate", 0)))
    except (TypeError, ValueError):
        return 0


def _canonical_thread_context(thread: Mapping[str, Any]) -> str:
    """Return bounded, quote-stripped canonical history for disposition checks."""
    messages = thread.get("messages")
    if not isinstance(messages, list):
        return ""
    canonical: list[str] = []
    for item in messages[-20:]:
        if not isinstance(item, Mapping):
            continue
        body = item.get("body")
        if not isinstance(body, str):
            continue
        text = latest_message_text(body)
        if not text:
            continue
        sender = item.get("from")
        sender_text = sender if isinstance(sender, str) else "unknown"
        role = "Varla" if is_internal_sender(sender_text) else "Creator"
        canonical.append(f"[{role}: {sender_text}]\n{text}")
    return "\n\n".join(canonical)[-50_000:]


def _same_sender_thread_context(
    thread: Mapping[str, Any],
    canonical_sender: str | None,
) -> str:
    """Return bounded message text authored by the exact latest sender."""
    if canonical_sender is None:
        return ""
    messages = thread.get("messages")
    if not isinstance(messages, list):
        return ""
    bodies: list[str] = []
    for item in messages[-20:]:
        if not isinstance(item, Mapping):
            continue
        if parse_mailbox(item.get("from")) != canonical_sender:
            continue
        body = item.get("body")
        if not isinstance(body, str):
            continue
        text = latest_message_text(body)
        if text:
            bodies.append(text)
    return "\n\n".join(bodies)[-50_000:]


class ProductionRecognition:
    """Search Gmail, re-read complete threads, classify, and persist tasks."""

    def __init__(
        self,
        database: Database,
        gmail: GmailGateway,
        *,
        credentials_path: str | Path,
        token_path: str | Path,
    ) -> None:
        self.database = database
        self.gmail = gmail
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._scan_lock = threading.Lock()

    def _resolve_answered_thread(
        self,
        thread_id: str,
        latest_message_id: str | None,
    ) -> int:
        """Hide pending local tasks when Gmail shows Varla replied last."""
        resolved = 0
        updated_at = _now()
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE gmail_thread_id = ? "
                "AND state NOT IN ('completed', 'ignored', 'executing')",
                (thread_id,),
            ).fetchall()
            for row in rows:
                payload = _payload(row)
                payload["thread_resolution"] = {
                    "status": "answered_in_gmail",
                    "latest_message_id": latest_message_id,
                    "updated_at": updated_at,
                }
                connection.execute(
                    "UPDATE tasks SET state = 'ignored', payload_json = ?, "
                    "updated_at = ? WHERE id = ?",
                    (_json(payload), updated_at, row["id"]),
                )
                self.database.append_audit(
                    task_id=row["id"],
                    action="gmail_thread_already_answered",
                    actor="production_recognition",
                    details={"latest_message_id": latest_message_id},
                    connection=connection,
                )
                resolved += 1
        return resolved

    def _record_sent_thread(
        self,
        thread_id: str,
        thread: Mapping[str, Any],
    ) -> int:
        """Mirror Gmail's latest internal reply into the local Sent view."""
        latest = _latest_message(thread)
        if latest is None:
            return 0
        latest_sender = latest.get("from")
        if not (
            isinstance(latest_sender, str)
            and is_internal_sender(latest_sender)
        ):
            return 0
        message_id = latest.get("message_id")
        if not isinstance(message_id, str) or not message_id:
            return 0

        messages = thread.get("messages")
        candidates = (
            [item for item in messages if isinstance(item, Mapping)]
            if isinstance(messages, list)
            else []
        )
        external_messages = [
            item
            for item in candidates
            if isinstance(item.get("from"), str)
            and not is_internal_sender(str(item.get("from")))
        ]
        external = max(
            external_messages,
            key=lambda item: _message_internal_date(item),
            default=None,
        )
        correspondent = parse_mailbox(
            external.get("from") if external is not None else latest.get("to")
        )
        if correspondent is None or is_internal_sender(correspondent):
            return 0

        connection = self.database._connect()
        try:
            source = connection.execute(
                "SELECT * FROM tasks WHERE gmail_thread_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
        finally:
            connection.close()
        source_payload = _payload(source) if source is not None else {}
        subject = latest.get("subject")
        if not isinstance(subject, str) or not subject:
            subject = external.get("subject") if external is not None else ""
        group = source["group_name"] if source is not None else "manual"
        payload = {
            "sender": correspondent,
            "subject": subject if isinstance(subject, str) else "",
            "message_internal_date": (
                latest.get("internal_date") or latest.get("internalDate")
            ),
            "message_date": latest.get("date"),
            "labels": latest.get("label_ids", ["SENT"]),
            "classification": source_payload.get("classification", {}),
            "decision": source_payload.get("decision", {}),
            "sent_sync": {
                "status": "confirmed_in_gmail",
                "outgoing_message_id": message_id,
            },
        }
        idempotency_key = f"gmail-sent:{thread_id}:{message_id}"
        try:
            with self.database.transaction() as connection:
                task = self.database.create_task(
                    idempotency_key=idempotency_key,
                    state="completed",
                    group=group,
                    gmail_thread_id=thread_id,
                    source_message_id=message_id,
                    payload=payload,
                    connection=connection,
                )
                self.database.append_audit(
                    task_id=task.id,
                    action="gmail_sent_synced",
                    actor="production_recognition",
                    details={"outgoing_message_id": message_id},
                    connection=connection,
                )
            return 1
        except sqlite3.IntegrityError:
            return 0

    def _require_credentials(self) -> None:
        if not self.credentials_path.is_file() or not self.token_path.is_file():
            raise GatewayError(
                "credentials_missing",
                "Gmail connection files are missing; authorization is required.",
            )

    def _search_recognition_messages(
        self,
        query: str,
    ) -> list[Mapping[str, Any]]:
        """Read a capped month search in bounded five-day windows.

        The guarded Gmail adapter intentionally caps each request at 50. When
        the broad month query reaches that cap, older duplicates must not hide
        newer unanswered threads deeper in the same month.
        """
        searches = [self.gmail.search(query, max_results=50)]
        first_raw = searches[0].get("messages")
        if isinstance(first_raw, list) and len(first_raw) >= 50:
            for newest_age in range(0, 30, 5):
                oldest_age = newest_age + 5
                window = f"newer_than:{oldest_age}d"
                if newest_age:
                    window = f"older_than:{newest_age}d {window}"
                searches.append(
                    self.gmail.search(f"{query} {window}", max_results=50)
                )

        messages: list[Mapping[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for search in searches:
            raw = search.get("messages")
            if not isinstance(raw, list):
                continue
            for item in raw:
                if not isinstance(item, Mapping):
                    continue
                key = (str(item.get("thread_id") or ""), str(item.get("message_id") or ""))
                if key in seen:
                    continue
                seen.add(key)
                messages.append(item)
        return messages

    def _reconcile_pending_threads(
        self,
        thread_cache: dict[str, Mapping[str, Any]],
    ) -> dict[str, int]:
        """Hide local work whose exact Gmail thread was answered elsewhere."""
        cutoff_ms = int(
            (datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000
        )
        connection = self.database._connect()
        try:
            rows = connection.execute(
                "SELECT DISTINCT gmail_thread_id FROM tasks "
                "WHERE gmail_thread_id IS NOT NULL "
                "AND state NOT IN "
                "('completed', 'ignored', 'executing') "
                "AND CASE WHEN CAST(json_extract(payload_json, "
                "'$.message_internal_date') AS INTEGER) >= 1000000000000 "
                "THEN CAST(json_extract(payload_json, "
                "'$.message_internal_date') AS INTEGER) "
                "ELSE CAST(strftime('%s', created_at) AS INTEGER) * 1000 "
                "END >= ? "
                "ORDER BY gmail_thread_id LIMIT 200"
                ,
                (cutoff_ms,),
            ).fetchall()
        finally:
            connection.close()

        checked = 0
        answered = 0
        failed = 0
        for row in rows:
            thread_id = row["gmail_thread_id"]
            if not isinstance(thread_id, str) or not thread_id:
                continue
            try:
                thread = thread_cache.get(thread_id)
                if thread is None:
                    thread = self.gmail.thread_read(thread_id)
                    thread_cache[thread_id] = thread
                checked += 1
                latest = _latest_message(thread)
                if latest is None:
                    failed += 1
                    continue
                latest_sender = latest.get("from")
                if not (
                    isinstance(latest_sender, str)
                    and is_internal_sender(latest_sender)
                ):
                    continue
                latest_message_id = latest.get("message_id")
                answered += self._resolve_answered_thread(
                    thread_id,
                    latest_message_id
                    if isinstance(latest_message_id, str)
                    else None,
                )
                self._record_sent_thread(thread_id, thread)
            except GatewayError:
                # A failed read must never hide the task. The operator can retry.
                failed += 1
        return {"checked": checked, "answered": answered, "failed": failed}

    def reconcile_pending(self) -> dict[str, object]:
        self._require_credentials()
        result = self._reconcile_pending_threads({})
        return {"status": "completed", **result}

    def sync_sent(self) -> dict[str, object]:
        """Sync recent Gmail Sent threads without sending or modifying Gmail."""
        self._require_credentials()
        with self._scan_lock:
            # Sent is a latest-status surface, not a historical work queue.
            # Reading the newest bounded page keeps this explicit refresh fast
            # and prevents one click from opening hundreds of Gmail processes.
            search = self.gmail.search(
                "in:sent newer_than:30d", max_results=50
            )
            raw_messages = search.get("messages")
            messages = raw_messages if isinstance(raw_messages, list) else []
            seen_threads: set[str] = set()
            checked = 0
            synced = 0
            failed = 0
            for item in messages:
                thread_id = item.get("thread_id") if isinstance(item, Mapping) else None
                if (
                    not isinstance(thread_id, str)
                    or not thread_id
                    or thread_id in seen_threads
                ):
                    continue
                seen_threads.add(thread_id)
                try:
                    thread = self.gmail.thread_read(thread_id)
                    checked += 1
                    synced += self._record_sent_thread(thread_id, thread)
                except GatewayError:
                    failed += 1
            return {
                "status": "completed",
                "checked": checked,
                "synced": synced,
                "failed": failed,
            }

    def _search_junk_messages(self, query: str) -> list[Mapping[str, Any]]:
        first = self.gmail.search(query, max_results=50)
        raw = first.get("messages")
        searches = [first]
        if isinstance(raw, list) and len(raw) >= 50:
            after_match = re.search(r"\bafter:(\d{4}/\d{2}/\d{2})", query)
            before_match = re.search(r"\bbefore:(\d{4}/\d{2}/\d{2})", query)
            if after_match and before_match:
                start = datetime.strptime(after_match.group(1), "%Y/%m/%d")
                end = datetime.strptime(before_match.group(1), "%Y/%m/%d")
                base = re.sub(r"\s*\b(?:after|before):\d{4}/\d{2}/\d{2}", "", query)
                cursor = start
                while cursor < end:
                    # Historical sweeps can span years. Month-sized windows
                    # stay below Gmail's bounded search surface in normal
                    # operation without spawning hundreds of CLI processes.
                    # Re-running the sweep exposes any month that itself hit
                    # the 50-message cap after the first verified batch moves
                    # to recoverable Trash.
                    window_end = min(cursor + timedelta(days=30), end)
                    window_query = (
                        f"{base} after:{cursor:%Y/%m/%d} "
                        f"before:{window_end:%Y/%m/%d}"
                    )
                    searches.append(self.gmail.search(window_query, max_results=50))
                    cursor = window_end

        messages: list[Mapping[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for search in searches:
            items = search.get("messages")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                key = (str(item.get("thread_id") or ""), str(item.get("message_id") or ""))
                if key in seen:
                    continue
                seen.add(key)
                messages.append(item)
        return messages

    def cleanup_junk(
        self,
        *,
        query: str = JUNK_CLEANUP_QUERY,
        dry_run: bool = False,
        include_blocked_senders: bool = True,
    ) -> dict[str, object]:
        """Move only deterministic service advertising to recoverable Trash."""
        self._require_credentials()
        if not self._scan_lock.acquire(blocking=False):
            return {"status": "busy", "auto_trashed": 0, "ambiguous_kept": 0}
        try:
            messages = self._search_junk_messages(query)
            blocked = (
                [
                    item["sender"]
                    for item in sorted(
                        self.database.list_blocked_senders(),
                        key=lambda value: str(value.get("updated_at") or ""),
                        reverse=True,
                    )[:MAX_BLOCKED_SENDER_SCAN]
                    if isinstance(item.get("sender"), str) and item["sender"]
                ]
                if include_blocked_senders
                else []
            )
            for offset in range(0, len(blocked), 20):
                chunk = blocked[offset : offset + 20]
                scope = query.split("{", 1)[0].strip()
                result = self.gmail.search(
                    scope + " {"
                    + " ".join(f"from:{sender}" for sender in chunk)
                    + "}",
                    max_results=50,
                )
                raw = result.get("messages")
                if isinstance(raw, list):
                    messages.extend(raw)

            seen_threads: set[str] = set()
            auto_trashed = 0
            candidates = 0
            ambiguous_kept = 0
            failed = 0
            for item in messages:
                if not isinstance(item, Mapping):
                    continue
                thread_id = item.get("thread_id")
                if not isinstance(thread_id, str) or not thread_id or thread_id in seen_threads:
                    continue
                seen_threads.add(thread_id)
                try:
                    thread = self.gmail.thread_read(thread_id)
                    latest = _latest_message(thread)
                    if latest is None:
                        failed += 1
                        continue
                    sender = latest.get("from")
                    message_id = latest.get("message_id")
                    body = latest.get("body")
                    if not all(isinstance(value, str) and value for value in (sender, message_id, body)):
                        failed += 1
                        continue
                    if is_internal_sender(sender):
                        continue
                    canonical_sender = parse_mailbox(sender)
                    current_body = latest_message_text(body)
                    if canonical_sender is None or not current_body:
                        failed += 1
                        continue
                    is_blocked = self.database.is_sender_blocked(canonical_sender)
                    classification = classify_message(
                        subject=latest.get("subject") if isinstance(latest.get("subject"), str) else None,
                        body=current_body,
                        thread_context=_same_sender_thread_context(thread, canonical_sender),
                        latest_sender=sender,
                    )
                    if not is_blocked and "vendor_promotion" not in classification.risk_flags:
                        ambiguous_kept += 1
                        continue

                    candidates += 1
                    if dry_run:
                        continue

                    receipt = self.gmail.move_to_trash(thread_id, message_id, sender)
                    if (
                        receipt.get("verified") is not True
                        or receipt.get("status") not in {"trash_moved", "already_trash"}
                        or receipt.get("account") != "info@varlascooter.com"
                        or receipt.get("thread_id") != thread_id
                        or receipt.get("source_message_id") != message_id
                        or parse_mailbox(receipt.get("sender")) != canonical_sender
                    ):
                        failed += 1
                        continue

                    idempotency_key = f"gmail:{thread_id}:{message_id}"
                    payload = {
                        "sender": sender,
                        "subject": latest.get("subject") or "",
                        "classification": classification.model_dump(mode="json"),
                        "risk_flags": ["vendor_promotion"],
                        "trash_disposition": {
                            "status": receipt.get("status"),
                            "verified": True,
                            "matched_by": "blocked_sender" if is_blocked else "vendor_promotion",
                            "updated_at": _now(),
                        },
                    }
                    with self.database.transaction() as connection:
                        try:
                            task = self.database.create_task(
                                idempotency_key=idempotency_key,
                                state="ignored",
                                group="manual",
                                gmail_thread_id=thread_id,
                                source_message_id=message_id,
                                payload=payload,
                                connection=connection,
                            )
                        except sqlite3.IntegrityError:
                            task = self.database.get_task_by_idempotency_key(idempotency_key)
                            if task is None:
                                raise
                            connection.execute(
                                "UPDATE tasks SET state = 'ignored', group_name = 'manual', "
                                "payload_json = ?, updated_at = ? WHERE id = ?",
                                (_json(payload), _now(), task.id),
                            )
                        self.database.block_sender(
                            canonical_sender,
                            reason="vendor_promotion",
                            source_task_id=task.id,
                            connection=connection,
                        )
                        self.database.append_audit(
                            task_id=task.id,
                            action="gmail_background_junk_trashed",
                            actor="production_recognition",
                            details={"rule": "vendor_promotion", "verified": True},
                            connection=connection,
                        )
                    auto_trashed += 1
                except GatewayError:
                    failed += 1
            return {
                "status": "preview" if dry_run else "completed",
                "candidates": candidates,
                "auto_trashed": auto_trashed,
                "ambiguous_kept": ambiguous_kept,
                "failed": failed,
            }
        finally:
            self._scan_lock.release()

    def recognize(self, query: str) -> dict[str, object]:
        with self._scan_lock:
            return self._recognize(query)

    def _recognize(self, query: str) -> dict[str, object]:
        self._require_credentials()
        thread_cache: dict[str, Mapping[str, Any]] = {}
        reconciliation = self._reconcile_pending_threads(thread_cache)
        messages = self._search_recognition_messages(query)
        blocked_sender_rows = self.database.list_blocked_senders()
        blocked_sender_addresses = [
            item["sender"]
            for item in blocked_sender_rows
            if isinstance(item.get("sender"), str) and item["sender"]
        ]
        for offset in range(0, len(blocked_sender_addresses), 20):
            sender_chunk = blocked_sender_addresses[offset : offset + 20]
            blocked_query = (
                "in:inbox newer_than:30d {"
                + " ".join(f"from:{sender}" for sender in sender_chunk)
                + "}"
            )
            blocked_search = self.gmail.search(blocked_query, max_results=50)
            blocked_raw = blocked_search.get("messages")
            if isinstance(blocked_raw, list):
                messages.extend(blocked_raw)
        seen_threads: set[str] = set()
        created: list[str] = []
        alignment_ids: list[str] = []
        duplicates = 0
        refreshed = 0
        skipped = 0
        auto_trashed = 0
        trash_failed = 0
        blocked_senders = 0
        gmail_filters_created = 0
        gmail_filters_existing = 0
        gmail_filter_failed = 0
        answered = reconciliation["answered"]
        for item in messages:
            if not isinstance(item, Mapping):
                skipped += 1
                continue
            thread_id = item.get("thread_id")
            if not isinstance(thread_id, str) or not thread_id:
                skipped += 1
                continue
            if thread_id in seen_threads:
                continue
            seen_threads.add(thread_id)
            thread = thread_cache.get(thread_id)
            if thread is None:
                try:
                    thread = self.gmail.thread_read(thread_id)
                except GatewayError:
                    # One unusually large or temporarily unavailable thread
                    # must not cancel the rest of the month-wide inbox sync.
                    skipped += 1
                    continue
                thread_cache[thread_id] = thread
            latest = _latest_message(thread)
            if latest is None:
                skipped += 1
                continue
            latest_sender = latest.get("from")
            if isinstance(latest_sender, str) and is_internal_sender(latest_sender):
                latest_message_id = latest.get("message_id")
                answered += self._resolve_answered_thread(
                    thread_id,
                    latest_message_id if isinstance(latest_message_id, str) else None,
                )
                self._record_sent_thread(thread_id, thread)
                continue
            message_id = latest.get("message_id")
            body = latest.get("body")
            sender = latest.get("from")
            subject = latest.get("subject")
            if not all(
                isinstance(value, str) and value
                for value in (message_id, body, sender)
            ):
                skipped += 1
                continue
            current_body = latest_message_text(body)
            if not current_body:
                skipped += 1
                continue
            canonical_sender = parse_mailbox(sender)
            sender_thread_context = _same_sender_thread_context(
                thread,
                canonical_sender,
            )
            canonical_thread_context = _canonical_thread_context(thread)
            classification = classify_message(
                subject=subject if isinstance(subject, str) else None,
                body=current_body,
                thread_context=sender_thread_context,
                latest_sender=sender,
            )
            blocked_sender = bool(
                canonical_sender
                and self.database.is_sender_blocked(canonical_sender)
            )
            if blocked_sender and "vendor_promotion" not in classification.risk_flags:
                classification = classification.model_copy(
                    update={
                        "matched_rules": [
                            *classification.matched_rules,
                            "guard.blocked_sender_vendor",
                        ],
                        "risk_flags": [
                            *classification.risk_flags,
                            "vendor_promotion",
                        ],
                    }
                )
            task_payload = {
                "sender": sender,
                "subject": subject if isinstance(subject, str) else "",
                "body": current_body,
                "thread_context": canonical_thread_context,
                "creator_context": sender_thread_context,
                "context_version": 2,
                "message_internal_date": (
                    latest.get("internal_date") or latest.get("internalDate")
                ),
                "message_date": latest.get("date"),
                "snippet": item.get("snippet"),
                "labels": item.get("label_ids", []),
                "classification": classification.model_dump(mode="json"),
                "decision": _decision_envelope(
                    current_body,
                    classification,
                    thread_context=canonical_thread_context,
                    creator_context=sender_thread_context,
                ),
                "risk_flags": list(classification.risk_flags),
                "source_risk_flags": list(classification.risk_flags),
            }
            task = None
            created_now = False
            refreshed_now = False
            idempotency_key = f"gmail:{thread_id}:{message_id}"
            try:
                with self.database.transaction() as connection:
                    task = self.database.create_task(
                        idempotency_key=idempotency_key,
                        state="classified",
                        group=classification.primary_group,
                        gmail_thread_id=thread_id,
                        source_message_id=message_id,
                        payload=task_payload,
                        connection=connection,
                    )
                    self.database.append_audit(
                        task_id=task.id,
                        action="gmail_recognized",
                        actor="production_recognition",
                        details={
                            "group": classification.primary_group,
                            "matched_rules": classification.matched_rules,
                        },
                        connection=connection,
                    )
                created_now = True
            except sqlite3.IntegrityError:
                duplicates += 1
                task = self.database.get_task_by_idempotency_key(idempotency_key)
                if task is None:
                    raise
                context_changed = (
                    task.payload.get("context_version") != 2
                    or task.payload.get("creator_context")
                    != sender_thread_context
                    or task.payload.get("thread_context")
                    != canonical_thread_context
                )
                if (
                    task.state not in {"completed", "ignored"}
                    and context_changed
                ):
                    updated_at = _now()
                    old_preview = task.payload.get("preview")
                    edited_by_user = bool(
                        isinstance(old_preview, Mapping)
                        and old_preview.get("edited_by_user") is True
                    )
                    refreshed_payload = dict(task.payload)
                    refreshed_payload.update(task_payload)
                    refreshed_payload.pop("preview_blocker", None)
                    if not edited_by_user:
                        refreshed_payload.pop("preview", None)
                    refreshed_state = (
                        "manual_review" if edited_by_user else "classified"
                    )
                    with self.database.transaction() as connection:
                        connection.execute(
                            "UPDATE tasks SET state = ?, group_name = ?, "
                            "payload_json = ?, updated_at = ? WHERE id = ?",
                            (
                                refreshed_state,
                                classification.primary_group,
                                _json(refreshed_payload),
                                updated_at,
                                task.id,
                            ),
                        )
                        self.database.append_audit(
                            task_id=task.id,
                            action="gmail_context_refreshed",
                            actor="production_recognition",
                            details={
                                "context_version": 2,
                                "preserved_operator_edit": edited_by_user,
                            },
                            connection=connection,
                        )
                    task = self.database.get_task(task.id)
                    refreshed += 1
                    refreshed_now = not edited_by_user

            should_trash = bool(
                AUTO_TRASH_RISK_FLAGS.intersection(classification.risk_flags)
            )
            if should_trash and task is not None and canonical_sender is not None:
                matched_by = (
                    "blocked_sender" if blocked_sender else "vendor_promotion"
                )
                try:
                    disposition = self.gmail.move_to_trash(
                        thread_id,
                        message_id,
                        sender,
                    )
                    if (
                        disposition.get("verified") is not True
                        or disposition.get("status")
                        not in {"trash_moved", "already_trash"}
                    ):
                        raise GatewayError(
                            "trash_not_verified",
                            "Gmail did not verify the requested Trash state.",
                        )
                    receipt_sender = parse_mailbox(disposition.get("sender"))
                    if (
                        disposition.get("account") != "info@varlascooter.com"
                        or disposition.get("thread_id") != thread_id
                        or disposition.get("source_message_id") != message_id
                        or receipt_sender != canonical_sender
                    ):
                        raise GatewayError(
                            "trash_receipt_mismatch",
                            "Gmail Trash verification did not match the exact request.",
                        )
                except GatewayError as exc:
                    trash_failed += 1
                    updated_at = _now()
                    with self.database.transaction() as connection:
                        row = connection.execute(
                            "SELECT * FROM tasks WHERE id = ?", (task.id,)
                        ).fetchone()
                        if row is not None:
                            failed_payload = _payload(row)
                            failed_payload.pop("preview", None)
                            failed_payload["trash_disposition"] = {
                                "status": "failed",
                                "error_code": exc.code,
                                "matched_by": matched_by,
                                "updated_at": updated_at,
                            }
                            connection.execute(
                                "UPDATE tasks SET state = 'manual_review', "
                                "group_name = 'manual', payload_json = ?, updated_at = ? "
                                "WHERE id = ?",
                                (_json(failed_payload), updated_at, task.id),
                            )
                            self.database.append_audit(
                                task_id=task.id,
                                action="gmail_auto_trash_failed",
                                actor="production_recognition",
                                details={"error_code": exc.code},
                                connection=connection,
                            )
                    continue

                try:
                    filter_receipt = self.gmail.ensure_sender_trash_filter(
                        canonical_sender
                    )
                    filter_sender = parse_mailbox(filter_receipt.get("sender"))
                    filter_status = filter_receipt.get("status")
                    filter_id = filter_receipt.get("filter_id")
                    if (
                        filter_receipt.get("verified") is not True
                        or filter_receipt.get("account") != "info@varlascooter.com"
                        or filter_sender != canonical_sender
                        or filter_status not in {"filter_created", "filter_exists"}
                        or not isinstance(filter_id, str)
                        or not filter_id
                    ):
                        raise GatewayError(
                            "filter_receipt_mismatch",
                            "Gmail sender filter verification did not match.",
                        )
                    if filter_status == "filter_created":
                        gmail_filters_created += 1
                    else:
                        gmail_filters_existing += 1
                except GatewayError as exc:
                    gmail_filter_failed += 1
                    filter_receipt = {
                        "status": "failed",
                        "error_code": exc.code,
                        "verified": False,
                    }

                updated_at = _now()
                with self.database.transaction() as connection:
                    row = connection.execute(
                        "SELECT * FROM tasks WHERE id = ?", (task.id,)
                    ).fetchone()
                    if row is not None:
                        spam_payload = _payload(row)
                        spam_payload.pop("preview", None)
                        spam_payload["trash_disposition"] = {
                            "status": disposition.get("status"),
                            "verified": disposition.get("verified") is True,
                            "matched_by": matched_by,
                            "updated_at": updated_at,
                        }
                        spam_payload["gmail_sender_filter"] = {
                            "status": filter_receipt.get("status"),
                            "verified": filter_receipt.get("verified") is True,
                            "filter_id": filter_receipt.get("filter_id"),
                            "error_code": filter_receipt.get("error_code"),
                            "updated_at": updated_at,
                        }
                        connection.execute(
                            "UPDATE tasks SET state = 'ignored', group_name = 'manual', "
                            "payload_json = ?, updated_at = ? WHERE id = ?",
                            (_json(spam_payload), updated_at, task.id),
                        )
                        self.database.block_sender(
                            canonical_sender,
                            reason="vendor_promotion",
                            source_task_id=task.id,
                            connection=connection,
                        )
                        self.database.append_audit(
                            task_id=task.id,
                            action="gmail_auto_trashed",
                            actor="production_recognition",
                            details={
                                "status": disposition.get("status"),
                                "verified": disposition.get("verified") is True,
                                "rule": "vendor_promotion",
                                "matched_by": matched_by,
                                "gmail_filter_status": filter_receipt.get("status"),
                                "gmail_filter_id": filter_receipt.get("filter_id"),
                            },
                            connection=connection,
                        )
                auto_trashed += 1
                blocked_senders += 1
                continue

            if created_now and task is not None:
                created.append(task.id)
            if (created_now or refreshed_now) and task is not None:
                alignment_ids.append(task.id)
        return {
            "status": "accepted",
            "scope": "最近30天 KOL 合作与合作询问",
            "created": len(created),
            "task_ids": alignment_ids,
            "duplicates": duplicates,
            "refreshed": refreshed,
            "skipped": skipped,
            "auto_trashed": auto_trashed,
            "trash_failed": trash_failed,
            "blocked_senders": blocked_senders,
            "gmail_filters_created": gmail_filters_created,
            "gmail_filters_existing": gmail_filters_existing,
            "gmail_filter_failed": gmail_filter_failed,
            "answered": answered,
            "reconcile_checked": reconciliation["checked"],
            "reconcile_failed": reconciliation["failed"],
        }


class ProductionTaskActions:
    """CAS-protected local task operations plus explicit Gmail label action."""

    def __init__(
        self,
        database: Database,
        gmail: GmailGateway,
        reply_engine: ReplyEngine,
    ) -> None:
        self.database = database
        self.gmail = gmail
        self.reply_engine = reply_engine

    @staticmethod
    def _cas(row: sqlite3.Row, options: Mapping[str, object]) -> bool:
        expected = options.get("expected_updated_at")
        return expected is None or expected == row["updated_at"]

    def generate_preview(
        self, task_id: str, **options: object
    ) -> dict[str, object]:
        task = self.database.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        if task.state not in {
            "classified",
            "needs_knowledge",
            "manual_review",
            "previewed",
        }:
            return {"status": "invalid_state", "task_id": task_id}
        if task.group not in VALID_GROUPS:
            return {"status": "needs_reclassification", "task_id": task_id}
        stored_body = task.payload.get("body")
        if not isinstance(stored_body, str) or not stored_body.strip():
            return {"status": "needs_knowledge", "task_id": task_id}
        body = latest_message_text(stored_body)
        if not body:
            updated_at = _now()
            with self.database.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                if (
                    row is None
                    or row["updated_at"] != task.updated_at.isoformat()
                    or not self._cas(row, options)
                ):
                    return {"status": "stale", "task_id": task_id}
                current_payload = _payload(row)
                current_payload.pop("preview", None)
                connection.execute(
                    "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                    "WHERE id = ?",
                    (
                        "needs_knowledge",
                        _json(current_payload),
                        updated_at,
                        task_id,
                    ),
                )
                self.database.append_audit(
                    task_id=task_id,
                    action="preview_blocked",
                    actor="production_task_actions",
                    details={"status": "needs_knowledge", "reason": "empty_message"},
                    connection=connection,
                )
            return {
                "status": "needs_knowledge",
                "task_id": task_id,
                "warnings": ["The latest message body is empty."],
                "updated_at": updated_at,
            }
        sender = task.payload.get("sender")
        subject = task.payload.get("subject")
        classification = classify_message(
            subject=subject if isinstance(subject, str) else None,
            body=body,
            latest_sender=sender if isinstance(sender, str) else None,
        )
        stored_thread_context = task.payload.get("thread_context")
        thread_context = (
            stored_thread_context
            if isinstance(stored_thread_context, str)
            else stored_body
        )
        stored_creator_context = task.payload.get("creator_context")
        creator_context = (
            stored_creator_context
            if isinstance(stored_creator_context, str)
            else body
        )
        decision = _decision_envelope(
            body,
            classification,
            thread_context=thread_context,
            creator_context=creator_context,
        )
        reply_group = (
            classification.secondary_group
            if (
                classification.primary_group == "kol"
                and classification.secondary_group in VALID_GROUPS
            )
            else classification.primary_group
        )
        if reply_group not in VALID_GROUPS:
            target = (
                "manual_review"
                if classification.primary_group == "manual"
                else "needs_reclassification"
            )
            updated_at = _now()
            with self.database.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                if (
                    row is None
                    or row["updated_at"] != task.updated_at.isoformat()
                    or not self._cas(row, options)
                ):
                    return {"status": "stale", "task_id": task_id}
                current_payload = _payload(row)
                current_payload["classification"] = classification.model_dump(
                    mode="json"
                )
                current_payload["source_risk_flags"] = list(
                    classification.risk_flags
                )
                current_payload["decision"] = decision
                current_payload.pop("preview", None)
                connection.execute(
                    "UPDATE tasks SET state = ?, group_name = ?, payload_json = ?, "
                    "updated_at = ? WHERE id = ?",
                    (
                        target,
                        classification.primary_group,
                        _json(current_payload),
                        updated_at,
                        task_id,
                    ),
                )
                self.database.append_audit(
                    task_id=task_id,
                    action="preview_blocked",
                    actor="production_task_actions",
                    details={
                        "status": target,
                        "classification": classification.primary_group,
                        "risk_flags": list(classification.risk_flags),
                    },
                    connection=connection,
                )
            return {
                "status": target,
                "task_id": task_id,
                "warnings": ["Classification requires manual review."],
                "updated_at": updated_at,
            }
        persisted_group = classification.primary_group
        reply_context = classification.model_dump()
        reply_context.update(
            {
                "stage_id": decision["stage_id"],
                "platform": "gmail",
            }
        )
        requested_tone = (
            options.get("tone") if isinstance(options.get("tone"), str) else None
        )
        if (
            requested_tone in {None, "natural"}
            and decision["stage_id"]
            in {"decline_acknowledgement", "reconsideration_evidence_received"}
        ):
            # These database-disposition templates are already complete emails.
            # Preserve them verbatim instead of adding a generic opening that
            # makes unrelated thread outcomes look like the same canned reply.
            requested_tone = "short"
        preview = self.reply_engine.generate(
            body,
            reply_group,
            reply_context,
            source_risk_flags=task.payload.get("source_risk_flags", []),
            tone=requested_tone,
            thread_context={
                "sender": task.payload.get("sender"),
                "subject": task.payload.get("subject"),
                "platform": "gmail",
            },
        )
        if not preview.body:
            target = (
                "needs_knowledge"
                if preview.status == "needs_knowledge"
                else "manual_review"
            )
            with self.database.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                if (
                    row is None
                    or row["updated_at"] != task.updated_at.isoformat()
                    or not self._cas(row, options)
                ):
                    return {"status": "stale", "task_id": task_id}
                current_payload = _payload(row)
                current_payload["classification"] = classification.model_dump(
                    mode="json"
                )
                current_payload["source_risk_flags"] = list(
                    classification.risk_flags
                )
                current_payload["decision"] = decision
                current_payload["preview_blocker"] = {
                    "status": preview.status,
                    "warnings": list(preview.warnings),
                }
                connection.execute(
                    "UPDATE tasks SET state = ?, group_name = ?, payload_json = ?, "
                    "updated_at = ? "
                    "WHERE id = ?",
                    (
                        target,
                        persisted_group,
                        _json(current_payload),
                        _now(),
                        task_id,
                    ),
                )
                self.database.append_audit(
                    task_id=task_id,
                    action="preview_blocked",
                    actor="production_task_actions",
                    details={"status": preview.status, "warnings": preview.warnings},
                    connection=connection,
                )
            return {
                "status": preview.status,
                "task_id": task_id,
                "warnings": preview.warnings,
            }
        relevance = evaluate_reply_relevance(
            body,
            preview.body,
            provided_facts=decision["thread_facts"],
        )
        preview_payload = {
            "body": preview.body,
            "body_sha256": hashlib.sha256(
                preview.body.encode("utf-8")
            ).hexdigest(),
            "tone": requested_tone,
            "source_risk_flags": list(classification.risk_flags),
            "knowledge_version": preview.knowledge_version,
            "scenario_id": preview.scenario_id,
            "template_id": preview.template_id,
            "template_version": preview.template_version,
            "template_hash": preview.template_hash,
            "relevance": relevance,
            "sources": [
                {
                    "title": source.title,
                    "source": Path(source.source).name,
                    "version": source.version,
                    "content_hash": source.content_hash,
                }
                for source in preview.sources
            ],
        }
        fresh_high_risk = bool(
            set(classification.risk_flags) & HIGH_SOURCE_RISK_FLAGS
        )
        final_status = (
            "previewed"
            if preview.status == "previewed"
            and relevance["status"] == "matched"
            and not fresh_high_risk
            else "manual_review"
        )
        target_state = final_status
        updated_at = _now()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if (
                row is None
                or row["updated_at"] != task.updated_at.isoformat()
                or not self._cas(row, options)
            ):
                return {"status": "stale", "task_id": task_id}
            current_payload = _payload(row)
            if current_payload.get("body") != body:
                current_payload.setdefault("thread_context", stored_body)
                current_payload["body"] = body
            current_payload["classification"] = classification.model_dump(mode="json")
            current_payload["source_risk_flags"] = list(
                classification.risk_flags
            )
            current_payload["decision"] = decision
            current_payload["preview"] = preview_payload
            current_payload.pop("preview_blocker", None)
            connection.execute(
                "UPDATE tasks SET state = ?, group_name = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    (
                        (
                            "previewed"
                            if str(row["state"]) == "previewed"
                            else transition(str(row["state"]), "previewed")
                        )
                        if target_state == "previewed"
                        else target_state
                    ),
                    persisted_group,
                    _json(current_payload),
                    updated_at,
                    task_id,
                ),
            )
            self.database.append_audit(
                task_id=task_id,
                action="preview_generated",
                actor="production_task_actions",
                details={
                    "knowledge_version": preview.knowledge_version,
                    "source_count": len(preview.sources),
                    "relevance_status": relevance["status"],
                },
                connection=connection,
            )
        return {
            "status": final_status,
            "task_id": task_id,
            "preview": preview_payload,
            "warnings": [
                *preview.warnings,
                *(
                    [
                        "Generated content does not fully correspond to the "
                        "detected questions; manual review is required."
                    ]
                    if relevance["status"] != "matched"
                    else []
                ),
            ],
            "updated_at": updated_at,
        }

    def save_preview(
        self, task_id: str, **options: object
    ) -> dict[str, object]:
        body = options.get("body")
        expected_updated_at = options.get("expected_updated_at")
        expected_hash = options.get("expected_preview_hash")
        operator_override = options.get("operator_override") is True
        if (
            not isinstance(body, str)
            or not 1 <= len(body) <= 10_000
            or not isinstance(expected_updated_at, str)
            or (
                not operator_override
                and not isinstance(expected_hash, str)
            )
            or (
                expected_hash is not None
                and not isinstance(expected_hash, str)
            )
        ):
            raise ValueError("invalid preview save request")
        unsafe_controls = re.search(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", body
        )
        injected_header = re.search(
            r"(?im)^\s*(?:to|cc|bcc|from|reply-to|recipient)\s*:",
            body,
        )
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            current = _payload(row)
            preview = current.get("preview")
            preview = preview if isinstance(preview, Mapping) else {}
            current_hash = preview.get("body_sha256")
            if (
                row["updated_at"] != expected_updated_at
                or current_hash != expected_hash
            ):
                return {"status": "stale", "task_id": task_id}
            allowed_states = (
                {
                    "classified",
                    "previewed",
                    "manual_review",
                    "needs_knowledge",
                    "needs_reclassification",
                }
                if operator_override
                else {"previewed"}
            )
            if row["state"] not in allowed_states:
                return {"status": "invalid_state", "task_id": task_id}
            try:
                classification = Classification.model_validate(
                    current.get("classification")
                )
            except Exception:
                classification = None
            source_flags = current.get("source_risk_flags")
            source_flags = (
                [flag for flag in source_flags if isinstance(flag, str)]
                if isinstance(source_flags, list)
                else []
            )
            if classification is not None:
                source_flags = list(
                    dict.fromkeys(
                        [*classification.risk_flags, *source_flags]
                    )
                )
            sender = current.get("sender")
            sender = sender if isinstance(sender, str) else None
            if classification is None and not operator_override:
                decision = None
                policy_reasons = ["classification_invalid"]
            else:
                if operator_override:
                    policy_group = "kol"
                    policy_secondary = None
                    confidence = (
                        classification.confidence
                        if classification is not None
                        else 1.0
                    )
                    action = "reply"
                    recipient = sender
                else:
                    assert classification is not None
                    policy_group = classification.primary_group
                    policy_secondary = classification.secondary_group
                    confidence = classification.confidence
                    routed_group = (
                        classification.secondary_group
                        if classification.primary_group == "kol"
                        and classification.secondary_group is not None
                        else classification.primary_group
                    )
                    action = (
                        "reply"
                        if classification.primary_group == "kol"
                        and classification.secondary_group is None
                        else "forward"
                    )
                    recipient = (
                        sender
                        if action == "reply"
                        else GROUP_ROUTES[routed_group]["department"]
                    )
                decision = evaluate_action(
                    body,
                    policy_group,
                    confidence,
                    auto_mode=False,
                    secondary_group=policy_secondary,
                    latest_sender=sender,
                    latest_sender_external=True,
                    recipient=recipient,
                    action=action,
                    thread_conflict=False,
                    duplicate=False,
                    stale=False,
                    user_confirmed=operator_override,
                    exact_preview_confirmed=operator_override,
                    operator_override=operator_override,
                    source_risk_flags=source_flags,
                )
                policy_reasons = list(decision.reasons)
            local_risks: list[str] = []
            if unsafe_controls:
                local_risks.append("unsafe_control_character")
            if injected_header:
                local_risks.append("recipient_or_header_injection")
            blocked = (
                (classification is None and not operator_override)
                or bool(local_risks)
                or decision is None
                or decision.outcome == "BLOCK"
            )
            if blocked:
                reasons = list(dict.fromkeys([*local_risks, *policy_reasons]))
                connection.execute(
                    "UPDATE tasks SET state = 'manual_review', updated_at = ? "
                    "WHERE id = ?",
                    (_now(), task_id),
                )
                self.database.append_audit(
                    task_id=task_id,
                    action="preview_edit_blocked",
                    actor="local_user",
                    details={"reasons": reasons},
                    connection=connection,
                )
                return {
                    "status": "policy_blocked",
                    "task_id": task_id,
                    "reasons": reasons,
                }
            editable = dict(preview)
            base_hash = editable.get("base_generated_hash")
            if not isinstance(base_hash, str):
                base_hash = current_hash
            edited_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            editable.update(
                {
                    "body": body,
                    "body_sha256": edited_hash,
                    "edited_by_user": True,
                    "base_generated_hash": base_hash,
                    "proof": None,
                    "scenario_id": None,
                    "template_id": None,
                    "template_version": None,
                    "template_hash": None,
                    "warning": (
                        "User-edited preview; all knowledge and risk checks "
                        "will run again before sending."
                    ),
                }
            )
            current["preview"] = editable
            updated_at = _now()
            next_state = (
                "manual_review"
                if operator_override and row["state"] != "previewed"
                else str(row["state"])
            )
            connection.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (next_state, _json(current), updated_at, task_id),
            )
            self.database.append_audit(
                task_id=task_id,
                action="preview_saved_by_user",
                actor="local_user",
                details={
                    "body_sha256": edited_hash,
                    "base_generated_hash": base_hash,
                },
                connection=connection,
            )
        return {
            "status": next_state,
            "task_id": task_id,
            "preview": editable,
            "updated_at": updated_at,
        }

    def reclassify(
        self, task_id: str, **options: object
    ) -> dict[str, object]:
        group = options.get("group")
        reason = options.get("reason")
        if group not in {*VALID_GROUPS, "manual"}:
            raise ValueError("invalid group")
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            if not self._cas(row, options):
                return {"status": "stale", "task_id": task_id}
            if row["state"] in {"executing", "completed", "ignored"}:
                return {"status": "invalid_state", "task_id": task_id}
            current = _payload(row)
            current["manual_classification"] = {
                "group": group,
                "reason": reason,
            }
            existing_flags = current.get("source_risk_flags")
            safe_flags = (
                [
                    flag
                    for flag in existing_flags
                    if isinstance(flag, str) and flag
                ]
                if isinstance(existing_flags, list)
                else []
            )
            current["classification"] = Classification(
                primary_group=group,
                confidence=1.0,
                matched_rules=["manual.reclassification"],
                suggested_label="KOL" if group == "kol" else None,
                suggested_department=(
                    "support@varlascooter.com"
                    if group in {"pre-sales", "order-logistics"}
                    else (
                        "customer@varlascooter.com"
                        if group == "after-sales"
                        else None
                    )
                ),
                risk_flags=safe_flags,
            ).model_dump(mode="json")
            current.pop("preview", None)
            connection.execute(
                "UPDATE tasks SET state = 'classified', group_name = ?, "
                "payload_json = ?, updated_at = ? WHERE id = ?",
                (group, _json(current), _now(), task_id),
            )
            self.database.append_audit(
                task_id=task_id,
                action="task_reclassified",
                actor="local_user",
                details={"group": group, "reason": reason},
                connection=connection,
            )
        return {"status": "classified", "task_id": task_id, "group": group}

    def confirm_label(
        self, task_id: str, **options: object
    ) -> dict[str, object]:
        claim_id = uuid4().hex
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            if not self._cas(row, options):
                return {"status": "stale", "task_id": task_id}
            if (
                row["group_name"] != "kol"
                or not row["gmail_thread_id"]
                or row["state"] in {"executing", "completed", "ignored"}
            ):
                return {"status": "invalid_state", "task_id": task_id}
            current = _payload(row)
            label = current.get("label_action")
            if isinstance(label, Mapping) and label.get("status") == "completed":
                return {"status": "already_completed", "task_id": task_id}
            if isinstance(label, Mapping) and label.get("status") == "in_progress":
                return {"status": "in_progress", "task_id": task_id}
            current["label_action"] = {
                "status": "in_progress",
                "claim_id": claim_id,
            }
            connection.execute(
                "UPDATE tasks SET payload_json = ?, updated_at = ? WHERE id = ?",
                (_json(current), _now(), task_id),
            )
            thread_id = str(row["gmail_thread_id"])
        try:
            result = self.gmail.label_add(thread_id)
        except GatewayError:
            with self.database.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                current = _payload(row)
                if current.get("label_action", {}).get("claim_id") == claim_id:
                    current["label_action"] = {"status": "failed"}
                    connection.execute(
                        "UPDATE tasks SET payload_json = ?, updated_at = ? "
                        "WHERE id = ?",
                        (_json(current), _now(), task_id),
                    )
            raise
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            current = _payload(row)
            if current.get("label_action", {}).get("claim_id") != claim_id:
                return {"status": "stale", "task_id": task_id}
            current["label_action"] = {
                "status": "completed",
                "label": "KOL",
            }
            connection.execute(
                "UPDATE tasks SET payload_json = ?, updated_at = ? WHERE id = ?",
                (_json(current), _now(), task_id),
            )
            self.database.append_audit(
                task_id=task_id,
                action="kol_label_confirmed",
                actor="local_user",
                details={"label": "KOL"},
                connection=connection,
            )
        return {
            "status": "completed",
            "task_id": task_id,
            "label": "KOL",
            "gateway_status": result.get("status"),
        }

    def ignore(self, task_id: str, **options: object) -> dict[str, object]:
        return self._terminal_action(task_id, "ignored", options)

    def manual_review(
        self, task_id: str, **options: object
    ) -> dict[str, object]:
        return self._terminal_action(task_id, "manual_review", options)

    def _terminal_action(
        self,
        task_id: str,
        target: str,
        options: Mapping[str, object],
    ) -> dict[str, object]:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            if not self._cas(row, options):
                return {"status": "stale", "task_id": task_id}
            if row["state"] in {"executing", "completed", "ignored"}:
                return {"status": "invalid_state", "task_id": task_id}
            if target == "ignored":
                next_state = transition(str(row["state"]), "ignored")
            else:
                next_state = "manual_review"
            current = _payload(row)
            current[f"{target}_reason"] = options.get("reason")
            connection.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (next_state, _json(current), _now(), task_id),
            )
            self.database.append_audit(
                task_id=task_id,
                action=f"task_{target}",
                actor="local_user",
                details={"reason": options.get("reason")},
                connection=connection,
            )
        return {"status": target, "task_id": task_id}


class ProductionWorkflow:
    """Turn the exact visible preview into approval, then run safe workflow."""

    def __init__(
        self, database: Database, workflow: ConfirmedWorkflow
    ) -> None:
        self.database = database
        self.workflow = workflow

    def _approve(
        self,
        task_id: str,
        action: str,
        *,
        expected_updated_at: object,
        expected_preview_hash: object,
        operator_override: object,
    ) -> dict[str, object] | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            current = _payload(row)
            preview = current.get("preview")
            preview = preview if isinstance(preview, Mapping) else {}
            if (
                not isinstance(expected_updated_at, str)
                or not isinstance(expected_preview_hash, str)
                or row["updated_at"] != expected_updated_at
                or preview.get("body_sha256") != expected_preview_hash
            ):
                return {"status": "stale", "task_id": task_id}
            if row["state"] in {
                "approved",
                "retryable",
                "executing",
                "completed",
            }:
                return None
            current_state = str(row["state"])
            is_operator_override = operator_override is True
            if current_state == "manual_review" and not is_operator_override:
                return {"status": "operator_confirmation_required", "task_id": task_id}
            if current_state not in {"previewed", "manual_review"}:
                return {"status": "invalid_state", "task_id": task_id}
            if (
                not isinstance(preview, Mapping)
                or not isinstance(preview.get("body"), str)
                or not isinstance(preview.get("body_sha256"), str)
            ):
                return {"status": "needs_knowledge", "task_id": task_id}
            current["confirmed_action"] = action
            current["operator_override"] = is_operator_override
            connection.execute(
                "UPDATE tasks SET state = ?, payload_json = ?, updated_at = ? "
                "WHERE id = ?",
                (
                    transition(current_state, "approved"),
                    _json(current),
                    _now(),
                    task_id,
                ),
            )
            self.database.append_audit(
                task_id=task_id,
                action=f"{action}_approved",
                actor="local_user",
                details={
                    "body_sha256": preview["body_sha256"],
                    "operator_override": is_operator_override,
                },
                connection=connection,
            )
        return None

    def confirm_reply(self, task_id: str, **options: object) -> object:
        stopped = self._approve(
            task_id,
            "reply",
            expected_updated_at=options.get("expected_updated_at"),
            expected_preview_hash=options.get("expected_preview_hash"),
            operator_override=options.get("operator_override"),
        )
        return stopped or self.workflow.confirm_reply(task_id)

    def confirm_forward(self, task_id: str, **options: object) -> object:
        stopped = self._approve(
            task_id,
            "forward",
            expected_updated_at=options.get("expected_updated_at"),
            expected_preview_hash=options.get("expected_preview_hash"),
            operator_override=options.get("operator_override"),
        )
        return stopped or self.workflow.confirm_forward(task_id)


_GROUP_MARKER = re.compile(
    r"(?:^|\n)\s*(?:group|group_name|组别)\s*:\s*"
    r"(kol|pre-sales|order-logistics|after-sales)\s*(?:\n|$)",
    re.IGNORECASE,
)


def build_feishu_package(
    sections: list[dict[str, Any]],
    staging: Path,
    *,
    baseline: Path,
) -> None:
    """Build only a complete, explicitly grouped four-package generation."""

    grouped: dict[str, str] = {}
    revisions: set[str] = set()
    for section in sections:
        content = section.get("content")
        revision = section.get("revision")
        if not isinstance(content, str) or not isinstance(revision, str):
            raise ValueError("Feishu section metadata is incomplete")
        marker = _GROUP_MARKER.search(content)
        if marker is None:
            raise ValueError("Feishu section lacks an explicit group marker")
        group = marker.group(1).casefold()
        if group in grouped:
            raise ValueError("Feishu contains conflicting duplicate groups")
        grouped[group] = _GROUP_MARKER.sub("\n", content, count=1).strip()
        revisions.add(revision)
    if set(grouped) != VALID_GROUPS or len(revisions) != 1:
        raise ValueError("Feishu must provide four groups at one revision")
    revision = next(iter(revisions))
    if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", revision) is None:
        raise ValueError("Feishu revision identifier is invalid")
    source_bytes = "\n".join(grouped[group] for group in sorted(grouped)).encode()
    source = {
        "identifier": "feishu-kol-knowledge",
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
    }
    version = f"feishu-{revision}"
    for group in sorted(VALID_GROUPS):
        (staging / f"{group}.md").write_text(
            f"Source: {source['identifier']}\n"
            f"Version: {version}\n\n"
            f"## Route\n\nGroup: {group}\n\n"
            f"## Feishu synchronized\n\n{grouped[group]}\n",
            encoding="utf-8",
        )
    for filename in ("routing_rules.json", "product_canon.json", "risk_rules.json"):
        payload = json.loads((baseline / filename).read_text(encoding="utf-8"))
        payload.update(
            {
                "version": version,
                "source_versions": [version],
                "source": source,
            }
        )
        (staging / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    artifact_names = [
        *(f"{group}.md" for group in sorted(VALID_GROUPS)),
        "routing_rules.json",
        "product_canon.json",
        "risk_rules.json",
    ]
    artifacts = {
        name: {
            "bytes": (staging / name).stat().st_size,
            "sha256": hashlib.sha256((staging / name).read_bytes()).hexdigest(),
        }
        for name in artifact_names
    }
    packages = {
        group: {
            "filename": f"{group}.md",
            "sha256": artifacts[f"{group}.md"]["sha256"],
            "source_chunk_count": 1,
            "total_chunk_count": 2,
        }
        for group in VALID_GROUPS
    }
    manifest = {
        "format_version": "1",
        "version": version,
        "source_versions": [version],
        "source": source,
        "artifacts": artifacts,
        "packages": packages,
        "coverage": {
            "allowlisted_chunk_count": 0,
            "allowlisted_headings": [],
            "extracted_substantive_chunk_count": 4,
            "routed_source_chunk_count": 4,
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_knowledge_package(path: Path) -> bool:
    candidate = KnowledgeIndex.in_memory()
    candidate.rebuild_from_directory(path)
    return candidate.active_manifest_hash is not None


class LockedReplyEngine:
    """Serialize index reads with Feishu generation activation."""

    def __init__(
        self, engine: ReplyEngine, lock: threading.RLock
    ) -> None:
        self.engine = engine
        self.lock = lock

    def generate(self, *args: object, **kwargs: object) -> object:
        with self.lock:
            return self.engine.generate(*args, **kwargs)


class ProductionFeishu:
    def __init__(
        self,
        syncer: FeishuSyncer,
        index: KnowledgeIndex,
        lock: threading.RLock,
    ) -> None:
        self.syncer = syncer
        self.index = index
        self.lock = lock

    def check(self, *, force: bool = False) -> SyncResult:
        result = self.syncer.check(force=force)
        if result.status == "updated" and result.active_path:
            with self.lock:
                self.index.rebuild_from_directory(result.active_path)
        return result


def build_production_services(
    config: AppConfig,
    database: Database,
    *,
    gmail_runner: object | None = None,
    feishu_runner: object | None = None,
    feishu_which: object | None = None,
    catalog_seed_directory: str | Path | None = None,
    approved_catalog_hashes: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose real local services with injectable process boundaries."""

    credentials_path = config.data_dir / "gmail-credentials.json"
    token_path = config.data_dir / "gmail-token.json"
    gmail_kwargs: dict[str, object] = {}
    if gmail_runner is not None:
        gmail_kwargs["runner"] = gmail_runner
    command_runtime = resolve_runtime()
    gmail = GmailGateway(
        python_executable=command_runtime,
        script_path=Path.home()
        / ".codex"
        / "skills"
        / "varla-gmail-automation"
        / "scripts"
        / "gmail_automation.py",
        credentials_path=credentials_path,
        token_path=token_path,
        expected_account=config.expected_gmail_account,
        **gmail_kwargs,
    )
    index_path = config.data_dir / "knowledge-index.sqlite3"
    index = KnowledgeIndex(
        sqlite3.connect(index_path, check_same_thread=False)
    )
    index.initialize()
    knowledge_root = config.project_dir / "knowledge"
    state_path = config.data_dir / "feishu-sync-state.json"
    if state_path.is_file():
        try:
            sync_state = json.loads(state_path.read_text(encoding="utf-8"))
            active = sync_state.get("active_path")
            candidate = Path(active) if isinstance(active, str) else None
            generations = (
                config.data_dir / "feishu-generations"
            ).resolve()
            if (
                candidate is not None
                and candidate.is_dir()
                and candidate.resolve().is_relative_to(generations)
            ):
                validate_knowledge_package(candidate)
                knowledge_root = candidate
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            pass
    index.rebuild_from_directory(knowledge_root)
    knowledge_lock = threading.RLock()
    reply_seed = (
        Path(catalog_seed_directory)
        if catalog_seed_directory is not None
        else config.reply_project_root / "knowledge_seed"
    )
    try:
        catalog = load_local_catalog(
            seed_directory=reply_seed,
            approved_hashes=approved_catalog_hashes,
        )
    except (FileNotFoundError, ValueError, OSError):
        catalog = LocalCatalog.empty(
            warnings=(
                "Catalog load failed; templates and product specifications "
                "are disabled.",
            ),
            requires_manual_review=True,
        )
    reply_engine = LockedReplyEngine(
        ReplyEngine(index, catalog=catalog), knowledge_lock
    )
    task_actions = ProductionTaskActions(database, gmail, reply_engine)
    workflow = ProductionWorkflow(
        database,
        ConfirmedWorkflow(database, gmail, reply_engine),
    )
    sync_kwargs: dict[str, object] = {}
    if feishu_runner is not None:
        sync_kwargs["runner"] = feishu_runner
    if feishu_which is not None:
        sync_kwargs["which"] = feishu_which
    syncer = FeishuSyncer(
        state_path=state_path,
        local_cache=config.data_dir / "knowledge-cache",
        rebuilder=lambda sections, staging: build_feishu_package(
            sections, staging, baseline=config.project_dir / "knowledge"
        ),
        validator=validate_knowledge_package,
        **sync_kwargs,
    )
    health = SkillHealthChecker(
        python_executable=command_runtime,
        lock_path=config.project_dir / "skills-lock.json",
        reply_project_root=config.reply_project_root,
        contract_output_root=config.data_dir / "contract-previews",
        gmail_credentials=GmailCredentials(
            credentials_path=credentials_path,
            token_path=token_path,
            expected_account=config.expected_gmail_account,
        ),
    )
    return {
        "recognition": ProductionRecognition(
            database,
            gmail,
            credentials_path=credentials_path,
            token_path=token_path,
        ),
        "workflow": workflow,
        "task_actions": task_actions,
        "feishu": ProductionFeishu(syncer, index, knowledge_lock),
        "health": health,
        "gmail": gmail,
        "knowledge_index": index,
    }


__all__ = [
    "ProductionRecognition",
    "ProductionTaskActions",
    "ProductionWorkflow",
    "build_feishu_package",
    "build_production_services",
    "validate_knowledge_package",
]
