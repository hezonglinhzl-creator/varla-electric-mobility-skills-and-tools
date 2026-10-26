"""Local-only HTTP API for the Varla KOL command center.

The API is deliberately dependency-injected: tests and the WebUI can exercise
the complete HTTP contract without contacting Gmail or Feishu.  Production
gateways are only called after an explicit POST from the local user.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.build_info import BUILD_ID, project_instance_id
from app.classifier import parse_mailbox
from app.config import AppConfig
from app.db import Database
from app.gmail_gateway import GatewayError, sanitize_error
from app.message_text import latest_message_text
from app.preview_alignment import PreviewAlignmentService
from app.redaction import redact_sensitive_json
from app.risk_policy import HARD_SOURCE_RISK_FLAGS, HIGH_SOURCE_RISK_FLAGS
from app.schemas import TASK_GROUPS, TASK_STATES
from app.service_links import LOCAL_TARGETS, open_local_target
from app.state_machine import InvalidTransition


_TASK_ID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_PRIVATE_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]|/(?:Users|home|tmp|var|etc)/)[^\s\"']*",
    re.IGNORECASE,
)
_SAFE_PAYLOAD_KEYS = frozenset(
    {
        "sender",
        "from",
        "subject",
        "snippet",
        "received_at",
        "message_internal_date",
        "message_date",
        "classification",
        "decision",
        "confidence",
        "reasons",
        "risk_flags",
        "routes",
        "labels",
        "preview",
        "forward_route",
        "source_risk_flags",
        "summary",
    }
)
_CONFLICT_STATUSES = frozenset(
    {
        "stale",
        "invalid_state",
        "invalid_transition",
        "needs_knowledge",
        "knowledge_conflict",
        "needs_reclassification",
        "classification_changed",
        "classification_failed",
        "preview_changed",
        "policy_blocked",
        "unsafe_recipient",
        "action_mismatch",
        "in_progress",
        "busy",
        "duplicate",
        "needs_reconciliation",
        "internal_reply",
        "invalid_source",
        "operator_confirmation_required",
    }
)
_UNAVAILABLE_STATUSES = frozenset(
    {"gateway_error", "gateway_failed", "unavailable", "error"}
)
_STATUS_DETAILS = {
    "stale": "邮件线程已变化，请重新识别并预览后再确认。",
    "invalid_state": "当前任务状态不允许执行该操作。",
    "invalid_transition": "当前任务状态不允许执行该操作。",
    "needs_knowledge": "知识依据不足，已停止执行，请人工补充知识。",
    "knowledge_conflict": "知识版本存在冲突，请重新同步并预览后再确认。",
    "needs_reclassification": "分类已变化，请重新分类后再操作。",
    "classification_changed": "分类已变化，请重新预览后再确认。",
    "classification_failed": "无法安全完成分类，请转人工处理。",
    "preview_changed": "回复预览已变化，请重新检查后再确认。",
    "policy_blocked": "风险规则已拦截该操作，请转人工处理。",
    "unsafe_recipient": "转发目标未通过固定白名单校验。",
    "action_mismatch": "该任务已有不同操作正在处理。",
    "in_progress": "该操作正在执行，请勿重复点击。",
    "busy": "该操作正在执行，请勿重复点击。",
    "duplicate": "该操作已提交，请勿重复点击。",
    "needs_reconciliation": "发送结果不确定，请先在 Gmail 中人工核对。",
    "internal_reply": "检测到内部邮件或循环风险，已停止执行。",
    "invalid_source": "邮件来源校验失败，已停止执行。",
    "operator_confirmation_required": "该任务需要你在确认窗口中完成二次人工确认。",
    "unavailable": "所需服务尚未配置或当前不可用。",
    "gateway_error": "外部服务暂时不可用，请检查连接后重试。",
    "gateway_failed": "外部服务暂时不可用，请检查连接后重试。",
    "error": "操作未完成，请检查服务状态后重试。",
}

KOL_RECOGNITION_QUERY = (
    'in:inbox newer_than:30d '
    '{KOL creator influencer collaboration cooperation partnership '
    'sponsorship sponsor affiliate commission ambassador review '
    '"content creator" "guest post" backlink "seo services" "link building" '
    '"shopify expert" "ecommerce expert" "e-commerce expert" '
    '"shopify agency" "conversion rate optimization" "sales optimization" '
    '"shopify community" "increase sales" "boost sales" "turn into buyers" '
    '"website performing" "not a sales pitch" 合作}'
)


class RecognitionService(Protocol):
    def recognize(self, query: str) -> object: ...

    def reconcile_pending(self) -> object: ...

    def sync_sent(self) -> object: ...

    def cleanup_junk(self) -> object: ...


class WorkflowService(Protocol):
    def confirm_reply(self, task_id: str, **options: object) -> object: ...

    def confirm_forward(self, task_id: str, **options: object) -> object: ...


class TaskActionService(Protocol):
    def generate_preview(self, task_id: str, **options: object) -> object: ...

    def save_preview(self, task_id: str, **options: object) -> object: ...

    def reclassify(self, task_id: str, **options: object) -> object: ...

    def confirm_label(self, task_id: str, **options: object) -> object: ...

    def ignore(self, task_id: str, **options: object) -> object: ...

    def manual_review(self, task_id: str, **options: object) -> object: ...


class FeishuService(Protocol):
    def check(self, *, force: bool = False) -> object: ...


class HealthService(Protocol):
    def run(self) -> object: ...

    def accept_verified_updates(self) -> object: ...


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RecognizeRequest(StrictModel):
    query: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("query")
    @classmethod
    def safe_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or _CONTROL_CHARACTERS.search(normalized):
            raise ValueError("query contains unsupported characters")
        return normalized


class ExpectedVersionRequest(StrictModel):
    expected_updated_at: str | None = Field(default=None, max_length=64)

    @field_validator("expected_updated_at")
    @classmethod
    def safe_version(cls, value: str | None) -> str | None:
        if value is not None and _CONTROL_CHARACTERS.search(value):
            raise ValueError("invalid expected_updated_at")
        return value


class PreviewRequest(ExpectedVersionRequest):
    tone: Literal["natural", "formal", "short"] = "natural"


class ConfirmSnapshotRequest(StrictModel):
    expected_updated_at: str = Field(min_length=1, max_length=64)
    expected_preview_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )

    @field_validator("expected_updated_at")
    @classmethod
    def safe_version(cls, value: str) -> str:
        if _CONTROL_CHARACTERS.search(value):
            raise ValueError("invalid expected_updated_at")
        return value


class ConfirmRequest(ConfirmSnapshotRequest):
    operator_override: bool = False


class SavePreviewRequest(StrictModel):
    body: str = Field(min_length=1, max_length=10_000)
    expected_updated_at: str = Field(min_length=1, max_length=64)
    expected_preview_hash: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    operator_override: bool = False

    @field_validator("expected_updated_at")
    @classmethod
    def safe_version(cls, value: str) -> str:
        if _CONTROL_CHARACTERS.search(value):
            raise ValueError("invalid expected_updated_at")
        return value


class ReclassifyRequest(ExpectedVersionRequest):
    group: Literal[
        "kol", "pre-sales", "order-logistics", "after-sales", "manual"
    ]
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def safe_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or _CONTROL_CHARACTERS.search(normalized):
            raise ValueError("invalid reason")
        return normalized


class ReasonRequest(ExpectedVersionRequest):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def safe_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or _CONTROL_CHARACTERS.search(normalized):
            raise ValueError("invalid reason")
        return normalized


class EmptyRequest(StrictModel):
    pass


class SyncRequest(StrictModel):
    force: bool = False


class ServiceUnavailable(RuntimeError):
    """Raised when a deliberately unconfigured adapter is requested."""


@dataclass(slots=True)
class ApiServices:
    recognition: RecognitionService
    workflow: WorkflowService
    task_actions: TaskActionService
    feishu: FeishuService
    health: HealthService


class RuntimeState:
    """Small durable pause switch. Auto mode is never persisted or enabled."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def _read(self) -> tuple[bool, str | None]:
        try:
            self.path.stat()
        except FileNotFoundError:
            return False, None
        except OSError:
            return True, "控制状态文件无法读取，系统已安全暂停。"
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return True, "控制状态文件无法读取，系统已安全暂停。"
        if (
            not isinstance(value, dict)
            or set(value) != {"paused"}
            or type(value.get("paused")) is not bool
        ):
            return True, "控制状态文件格式无效，系统已安全暂停。"
        return value["paused"], None

    def paused(self) -> bool:
        with self._lock:
            return self._read()[0]

    def error(self) -> str | None:
        with self._lock:
            return self._read()[1]

    def snapshot(self) -> tuple[bool, str | None]:
        with self._lock:
            return self._read()

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(
                f".{self.path.name}.{uuid4().hex}.tmp"
            )
            temporary.write_text(
                json.dumps({"paused": bool(paused)}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.path)


def _safe_string(value: str) -> str:
    value = _PRIVATE_PATH.sub("[REDACTED_PATH]", value)
    return sanitize_error(value)


def _safe_value(value: object) -> object:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        redacted = redact_sensitive_json(dict(value))
        return {str(key): _safe_value(item) for key, item in redacted.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, Path):
        return "[REDACTED_PATH]"
    if isinstance(value, str):
        return _safe_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _safe_string(str(value))


def _row_payload(row: sqlite3.Row) -> dict[str, object]:
    try:
        payload = json.loads(row["payload_json"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _task_message_time_ms(row: sqlite3.Row) -> int:
    """Return the Gmail message time, falling back to the local row time."""
    payload = _row_payload(row)
    raw = payload.get("message_internal_date")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    if value >= 1_000_000_000_000:
        return value
    try:
        return int(datetime.fromisoformat(str(row["created_at"])).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def _is_hidden_marketing_task(
    row: sqlite3.Row, blocked_senders: set[str]
) -> bool:
    payload = _row_payload(row)
    classification = payload.get("classification")
    classification = (
        classification if isinstance(classification, Mapping) else {}
    )
    raw_flags: list[object] = []
    for candidate in (
        payload.get("risk_flags"),
        payload.get("source_risk_flags"),
        classification.get("risk_flags"),
    ):
        if isinstance(candidate, list):
            raw_flags.extend(candidate)
    if "vendor_promotion" in raw_flags:
        return True

    matched_rules = classification.get("matched_rules")
    if isinstance(matched_rules, list) and any(
        rule in {"guard.vendor_promotion", "guard.blocked_sender_vendor"}
        for rule in matched_rules
    ):
        return True

    disposition = payload.get("trash_disposition")
    if isinstance(disposition, Mapping) and disposition.get("matched_by") in {
        "vendor_promotion",
        "blocked_sender",
    }:
        return True

    sender = payload.get("sender") or payload.get("from")
    canonical_sender = parse_mailbox(sender if isinstance(sender, str) else None)
    return canonical_sender in blocked_senders if canonical_sender else False


def _task_projection(row: sqlite3.Row) -> dict[str, object]:
    payload = _row_payload(row)
    public_payload = {
        key: value for key, value in payload.items() if key in _SAFE_PAYLOAD_KEYS
    }
    message_body = payload.get("body")
    if isinstance(message_body, str):
        public_payload["message_body"] = latest_message_text(message_body)
    return {
        "id": row["id"],
        "state": row["state"],
        "group": row["group_name"],
        "gmail_thread_id": row["gmail_thread_id"],
        "source_message_id": row["source_message_id"],
        "payload": _safe_value(public_payload),
        "capabilities": _task_capabilities(row, payload),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _task_capabilities(
    row: sqlite3.Row, payload: Mapping[str, object]
) -> dict[str, object]:
    state = str(row["state"])
    group = str(row["group_name"])
    classification = payload.get("classification")
    classification = (
        classification if isinstance(classification, Mapping) else {}
    )
    primary = classification.get("primary_group")
    primary = primary if isinstance(primary, str) else group
    secondary = classification.get("secondary_group")
    secondary = secondary if isinstance(secondary, str) else None
    raw_flags: list[object] = []
    for candidate in (
        payload.get("risk_flags"),
        payload.get("source_risk_flags"),
        classification.get("risk_flags"),
    ):
        if isinstance(candidate, list):
            raw_flags.extend(candidate)
    flags = {flag for flag in raw_flags if isinstance(flag, str)}
    preview_blocker = payload.get("preview_blocker")
    preview_blocker = (
        preview_blocker if isinstance(preview_blocker, Mapping) else {}
    )
    knowledge_blocked = preview_blocker.get("status") in {
        "needs_knowledge",
        "manual_review",
        "knowledge_conflict",
    }
    hard_blocked = bool(flags & HARD_SOURCE_RISK_FLAGS)
    terminal = state in {"executing", "completed", "ignored", "replied", "forwarded"}
    preview = payload.get("preview")
    preview = preview if isinstance(preview, Mapping) else {}
    preview_ready = bool(
        isinstance(preview.get("body"), str)
        and preview.get("body")
        and isinstance(preview.get("body_sha256"), str)
    )
    confirmable = (
        state in {"previewed", "manual_review"}
        and preview_ready
        and not terminal
        and not hard_blocked
        and not knowledge_blocked
    )
    routed_group = secondary if primary == "kol" and secondary else primary
    routes = {
        "pre-sales": "support@varlascooter.com",
        "order-logistics": "support@varlascooter.com",
        "after-sales": "customer@varlascooter.com",
    }
    forward_recipient = routes.get(routed_group)
    can_reply = confirmable and primary == "kol" and secondary is None
    can_forward = confirmable and forward_recipient is not None
    has_gmail_source = all(
        isinstance(row[name], str) and bool(row[name])
        for name in ("gmail_thread_id", "source_message_id")
    )
    can_manual_reply = bool(
        has_gmail_source
        and not terminal
        and not hard_blocked
        and (
            can_reply
            or group == "manual"
            or state
            in {
                "classified",
                "manual_review",
                "needs_knowledge",
                "needs_reclassification",
            }
        )
    )
    can_label = (
        group == "kol"
        and not terminal
        and state not in {"manual_review", "needs_reclassification"}
    )
    if knowledge_blocked:
        blocked_reason = "knowledge_conflict"
    elif hard_blocked:
        blocked_reason = "risk_policy_blocked"
    elif terminal:
        blocked_reason = "task_is_terminal"
    elif not confirmable:
        blocked_reason = "preview_not_ready"
    elif not can_reply and not can_forward:
        blocked_reason = "route_not_available"
    else:
        blocked_reason = None
    return {
        "can_reply": can_reply,
        "can_manual_reply": can_manual_reply,
        "can_forward": can_forward,
        "forward_recipient": forward_recipient,
        "can_label": can_label,
        "blocked_reason": blocked_reason,
        "requires_operator_override": (
            confirmable
            and (
                state == "manual_review"
                or bool(flags & (HIGH_SOURCE_RISK_FLAGS - HARD_SOURCE_RISK_FLAGS))
            )
        ),
        "hard_blocked": hard_blocked,
    }


class DatabaseView:
    """Read-only projections and audit pagination for the HTTP boundary."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def task(self, task_id: str) -> dict[str, object] | None:
        connection = self.database._connect()
        try:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            blocked_senders = {
                str(item["sender"])
                for item in connection.execute("SELECT sender FROM blocked_senders")
            }
            if row is None or _is_hidden_marketing_task(row, blocked_senders):
                return None
            return _task_projection(row)
        finally:
            connection.close()

    def tasks(
        self,
        *,
        group: str | None,
        state: str | None,
        exclude_state: str | None,
        issue_only: bool,
        limit: int,
        offset: int,
        pending_only: bool = False,
    ) -> list[dict[str, object]]:
        clauses: list[str] = []
        parameters: list[object] = []
        cutoff_ms = int(
            (datetime.now(UTC) - timedelta(days=30)).timestamp() * 1000
        )
        clauses.append(
            "CASE WHEN CAST(json_extract(payload_json, "
            "'$.message_internal_date') AS INTEGER) >= 1000000000000 "
            "THEN CAST(json_extract(payload_json, "
            "'$.message_internal_date') AS INTEGER) "
            "ELSE CAST(strftime('%s', created_at) AS INTEGER) * 1000 "
            "END >= ?"
        )
        parameters.append(cutoff_ms)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        connection = self.database._connect()
        try:
            rows = connection.execute(
                f"""
                SELECT * FROM tasks{where}
                ORDER BY created_at DESC, id DESC
                """,
                parameters,
            ).fetchall()
            blocked_senders = {
                str(item["sender"])
                for item in connection.execute("SELECT sender FROM blocked_senders")
            }
            manually_routed_ids = {
                str(item["task_id"])
                for item in connection.execute(
                    "SELECT DISTINCT task_id FROM audit_log "
                    "WHERE action = 'task_manual_review' AND task_id IS NOT NULL"
                )
            }
            # One correspondent owns one visible card.  Rank every recent row
            # before applying a page filter so an older completed reply cannot
            # remain in Sent after a newer incoming message reopens the sender.
            ranked_rows = sorted(
                rows,
                key=lambda row: (
                    _task_message_time_ms(row),
                    str(row["created_at"]),
                    str(row["id"]),
                ),
                reverse=True,
            )
            latest_rows: list[sqlite3.Row] = []
            seen_senders: set[str] = set()
            for row in ranked_rows:
                if _is_hidden_marketing_task(row, blocked_senders):
                    continue
                payload = _row_payload(row)
                raw_sender = payload.get("sender") or payload.get("from")
                sender = parse_mailbox(
                    raw_sender if isinstance(raw_sender, str) else None
                )
                sender_key = sender or f"task:{row['id']}"
                if sender_key in seen_senders:
                    continue
                seen_senders.add(sender_key)
                latest_rows.append(row)

            issue_states = {
                "needs_knowledge",
                "needs_reclassification",
                "manual_review",
                "retryable",
            }
            visible_rows = []
            for row in latest_rows:
                row_state = str(row["state"])
                if group is not None and row["group_name"] != group:
                    continue
                if state is not None and row_state != state:
                    continue
                if (
                    state == "manual_review"
                    and str(row["id"]) not in manually_routed_ids
                ):
                    continue
                if exclude_state is not None and row_state == exclude_state:
                    continue
                if pending_only and row_state in {
                    "completed",
                    "ignored",
                    "executing",
                }:
                    continue
                if (
                    pending_only
                    and row_state == "manual_review"
                    and str(row["id"]) in manually_routed_ids
                ):
                    continue
                if issue_only and row_state not in issue_states:
                    continue
                visible_rows.append(row)
            return [
                _task_projection(row)
                for row in visible_rows[offset : offset + limit]
            ]
        finally:
            connection.close()

    def audit(self, *, limit: int, offset: int) -> list[dict[str, object]]:
        connection = self.database._connect()
        try:
            rows = connection.execute(
                """
                SELECT id, task_id, action, actor, details_json, created_at
                FROM audit_log
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        finally:
            connection.close()
        records: list[dict[str, object]] = []
        for row in rows:
            try:
                details = json.loads(row["details_json"])
            except (TypeError, json.JSONDecodeError):
                details = {}
            records.append(
                {
                    "id": row["id"],
                    "task_id": row["task_id"],
                    "action": row["action"],
                    "actor": row["actor"],
                    "details": _safe_value(details),
                    "created_at": row["created_at"],
                }
            )
        return records


def _status_of(result: object) -> str | None:
    if isinstance(result, BaseModel):
        return getattr(result, "status", None)
    if isinstance(result, Mapping):
        value = result.get("status")
        return value if isinstance(value, str) else None
    return getattr(result, "status", None)


def _result_or_error(result: object, *, accepted: bool = False) -> JSONResponse:
    status = _status_of(result)
    safe = _safe_value(result)
    if status in _CONFLICT_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=_STATUS_DETAILS.get(status, "当前操作存在冲突，请刷新后重试。"),
        )
    if status in _UNAVAILABLE_STATUSES:
        raise HTTPException(
            status_code=503,
            detail=_STATUS_DETAILS.get(status, _STATUS_DETAILS["unavailable"]),
        )
    return JSONResponse(status_code=202 if accepted else 200, content=safe)


def _task_or_404(view: DatabaseView, task_id: str) -> dict[str, object]:
    task = view.task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return task


def _validate_task_id(task_id: str) -> str:
    if re.fullmatch(_TASK_ID_PATTERN, task_id) is None:
        raise HTTPException(status_code=422, detail="任务编号无效。")
    return task_id


def _options(payload: BaseModel | None) -> dict[str, object]:
    return {} if payload is None else payload.model_dump(exclude_none=True)


def _default_services(config: AppConfig, database: Database) -> ApiServices:
    from app.production_services import build_production_services

    composed = build_production_services(config, database)
    return ApiServices(
        recognition=composed["recognition"],  # type: ignore[arg-type]
        workflow=composed["workflow"],  # type: ignore[arg-type]
        task_actions=composed["task_actions"],  # type: ignore[arg-type]
        feishu=composed["feishu"],  # type: ignore[arg-type]
        health=composed["health"],  # type: ignore[arg-type]
    )


def create_app(
    *,
    config: AppConfig | None = None,
    database: Database | None = None,
    recognition_service: RecognitionService | None = None,
    workflow_service: WorkflowService | None = None,
    task_action_service: TaskActionService | None = None,
    feishu_service: FeishuService | None = None,
    health_service: HealthService | None = None,
    service_launcher: Callable[[str], object] | None = None,
    runtime_state: RuntimeState | None = None,
    testing: bool = False,
    junk_cleanup_interval_seconds: float = 10 * 60,
) -> FastAPI:
    """Create the local app without performing Gmail or Feishu I/O."""

    config = config or AppConfig.from_environment()
    if config.bind_host != "127.0.0.1":
        raise ValueError("bind_host must be exactly 127.0.0.1")
    config.ensure_runtime_dirs()
    database = database or Database(config.data_dir / "command-center.sqlite3")
    database.initialize()
    needs_defaults = any(
        service is None
        for service in (
            recognition_service,
            workflow_service,
            task_action_service,
            feishu_service,
            health_service,
        )
    )
    defaults = (
        _default_services(config, database) if needs_defaults else None
    )
    if defaults is None:
        assert (
            recognition_service is not None
            and workflow_service is not None
            and task_action_service is not None
            and feishu_service is not None
            and health_service is not None
        )
    services = ApiServices(
        recognition=(
            recognition_service
            if recognition_service is not None
            else defaults.recognition  # type: ignore[union-attr]
        ),
        workflow=(
            workflow_service
            if workflow_service is not None
            else defaults.workflow  # type: ignore[union-attr]
        ),
        task_actions=(
            task_action_service
            if task_action_service is not None
            else defaults.task_actions  # type: ignore[union-attr]
        ),
        feishu=(
            feishu_service
            if feishu_service is not None
            else defaults.feishu  # type: ignore[union-attr]
        ),
        health=(
            health_service
            if health_service is not None
            else defaults.health  # type: ignore[union-attr]
        ),
    )
    preview_alignment = PreviewAlignmentService(database, services.task_actions)
    state = runtime_state or RuntimeState(
        config.data_dir / "control-state.json"
    )
    instance_id = project_instance_id(config.project_dir)
    view = DatabaseView(database)
    cleanup_stop = threading.Event()
    cleanup_thread: threading.Thread | None = None

    def junk_cleanup_loop() -> None:
        while not cleanup_stop.is_set():
            if not state.paused():
                try:
                    app.state.last_junk_cleanup = services.recognition.cleanup_junk()
                except Exception as exc:  # keep the local UI alive on Gmail outages
                    app.state.last_junk_cleanup = {
                        "status": "failed",
                        "error": _safe_string(str(exc)),
                    }
            if cleanup_stop.wait(junk_cleanup_interval_seconds):
                break

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal cleanup_thread
        if not testing and hasattr(services.recognition, "cleanup_junk"):
            cleanup_thread = threading.Thread(
                target=junk_cleanup_loop,
                name="varla-junk-cleanup",
                daemon=True,
            )
            cleanup_thread.start()
        try:
            yield
        finally:
            cleanup_stop.set()
            if cleanup_thread is not None:
                cleanup_thread.join(timeout=2)

    app = FastAPI(
        title="Varla KOL Command Center",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.testing = bool(testing)
    app.state.config = config
    app.state.last_junk_cleanup = {"status": "starting"}
    launch_service = service_launcher or (
        lambda target: open_local_target(config, target)
    )
    app.state.services = services

    @app.middleware("http")
    async def local_mutation_guard(request: Request, call_next):
        raw_host = request.headers.get("host") or ""
        try:
            host = (urlsplit(f"//{raw_host}").hostname or "").lower()
        except ValueError:
            host = ""
        allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        allowed_clients = {"127.0.0.1", "::1"}
        if app.state.testing:
            allowed_hosts.add("testserver")
            allowed_clients.add("testclient")
        client_host = (
            request.client.host.lower() if request.client is not None else ""
        )
        if client_host not in allowed_clients or host not in allowed_hosts:
            return JSONResponse(
                status_code=403,
                content={"detail": "仅允许从本机总控页面访问。"},
            )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            origin_host = urlsplit(origin).hostname if origin else None
            if (
                (
                    origin is not None
                    and (
                        origin_host is None
                        or origin_host.lower() not in allowed_hosts
                    )
                )
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "仅允许从本机总控页面执行写操作。"},
                )
            business_mutation = (
                request.url.path == "/api/recognize"
                or request.url.path == "/api/feishu/sync"
                or request.url.path.startswith("/api/tasks/")
            )
            if business_mutation and state.paused():
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "系统已暂停，请先恢复后再执行该操作。"
                    },
                )
        return await call_next(request)

    @app.exception_handler(ServiceUnavailable)
    async def unavailable_handler(_request: Request, exc: ServiceUnavailable):
        return JSONResponse(
            status_code=503,
            content={"detail": _safe_string(str(exc))},
        )

    @app.exception_handler(GatewayError)
    async def gateway_handler(_request: Request, exc: GatewayError):
        details = {
            "credentials_missing": "Gmail 尚未连接，请先完成授权和邮箱验证。",
            "timeout": "Gmail 读取超过 30 秒，请检查网络后重新识别。",
            "launch_failed": "Gmail 读取工具无法启动，请运行外部服务检查。",
            "command_failed": "Gmail 读取工具执行失败，请运行外部服务检查。",
            "invalid_json": "Gmail 返回数据不完整，本次没有创建任务。",
            "gmail_api_error": "Gmail API 暂时不可用，请检查授权或网络后重试。",
            "dependency_missing": "Gmail 运行环境缺少必要组件，请运行外部服务检查；无需重新登录。",
            "stopped": "Gmail 安全检查已停止本次操作，请重新验证登录邮箱。",
        }
        detail = details.get(
            exc.code,
            "Gmail 外部服务暂时不可用，本次没有执行邮件动作。",
        )
        return JSONResponse(
            status_code=503,
            content={"detail": detail},
        )

    @app.exception_handler(InvalidTransition)
    async def transition_handler(_request: Request, _exc: InvalidTransition):
        return JSONResponse(
            status_code=409,
            content={"detail": _STATUS_DETAILS["invalid_transition"]},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, _exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={"detail": "请求参数无效，请检查输入。"},
        )

    @app.exception_handler(Exception)
    async def safe_exception_handler(_request: Request, _exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "本地服务发生错误，请查看审计记录后重试。"},
        )

    @app.get("/api/status")
    def get_status() -> dict[str, object]:
        paused, control_state_error = state.snapshot()
        return {
            "build_id": BUILD_ID,
            "instance_id": instance_id,
            "bind_host": "127.0.0.1",
            "bind_port": config.bind_port,
            "local_only": True,
            "manual_mode": True,
            "auto_mode": False,
            "junk_cleanup_enabled": not app.state.testing,
            "junk_cleanup_interval_seconds": junk_cleanup_interval_seconds,
            "junk_cleanup": _safe_value(app.state.last_junk_cleanup),
            "paused": paused,
            "control_state_error": control_state_error,
        }

    @app.get("/api/tasks")
    def get_tasks(
        group: str | None = Query(default=None),
        state_filter: str | None = Query(default=None, alias="state"),
        exclude_state: str | None = Query(default=None),
        pending_only: bool = Query(default=False),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
    ) -> list[dict[str, object]]:
        if group is not None and group not in TASK_GROUPS:
            raise HTTPException(status_code=422, detail="任务分组无效。")
        if state_filter is not None and state_filter not in TASK_STATES:
            raise HTTPException(status_code=422, detail="任务状态无效。")
        if exclude_state is not None and exclude_state not in TASK_STATES:
            raise HTTPException(status_code=422, detail="排除的任务状态无效。")
        return view.tasks(
            group=group,
            state=state_filter,
            exclude_state=exclude_state,
            issue_only=False,
            limit=limit,
            offset=offset,
            pending_only=pending_only,
        )

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, object]:
        _validate_task_id(task_id)
        return _task_or_404(view, task_id)

    @app.get("/api/issues")
    def get_issues(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
    ) -> list[dict[str, object]]:
        return view.tasks(
            group=None,
            state=None,
            exclude_state=None,
            issue_only=True,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/audit")
    def get_audit(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100_000),
    ) -> list[dict[str, object]]:
        return view.audit(limit=limit, offset=offset)

    def reject_if_paused() -> None:
        if state.paused():
            raise HTTPException(
                status_code=409, detail="系统已暂停，请先恢复后再执行该操作。"
            )

    @app.post("/api/recognize", status_code=202)
    def recognize(payload: RecognizeRequest | None = Body(default=None)):
        del payload
        reject_if_paused()
        recognized = services.recognition.recognize(KOL_RECOGNITION_QUERY)
        if not isinstance(recognized, Mapping):
            return _result_or_error(recognized, accepted=True)
        result = dict(recognized)
        # Recognition only fills the operator's home queue. Preview generation
        # is a separate, explicit button action; doing it here can move a new
        # task into manual review before the operator ever sees it.
        result["preview_alignment"] = {
            "eligible": 0,
            "generated": 0,
            "matched": 0,
            "manual_review": 0,
            "needs_knowledge": 0,
            "skipped": 0,
            "failed": 0,
        }
        return _result_or_error(
            result,
            accepted=True,
        )

    @app.post("/api/junk/cleanup")
    def cleanup_junk_mail():
        """Run the deterministic, recoverable Gmail junk cleanup on demand."""
        reject_if_paused()
        result = services.recognition.cleanup_junk()
        app.state.last_junk_cleanup = result
        return _result_or_error(result)

    @app.post("/api/tasks/reconcile-pending")
    def reconcile_pending_tasks():
        """Re-read pending Gmail threads after an explicit operator refresh."""
        return _result_or_error(services.recognition.reconcile_pending())

    @app.post("/api/tasks/sync-sent")
    def sync_sent_tasks():
        """Read recent Gmail Sent threads and refresh the local projection."""
        return _result_or_error(services.recognition.sync_sent())

    @app.post("/api/tasks/{task_id}/generate-preview")
    def generate_preview(
        task_id: str,
        payload: PreviewRequest | None = Body(default=None),
    ):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.task_actions.generate_preview(
                task_id, **_options(payload)
            )
        )

    @app.post("/api/tasks/{task_id}/save-preview")
    def save_preview(task_id: str, payload: SavePreviewRequest):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        options = _options(payload)
        if payload.operator_override is False:
            options.pop("operator_override", None)
        return _result_or_error(
            services.task_actions.save_preview(task_id, **options)
        )

    @app.post("/api/tasks/{task_id}/reclassify")
    def reclassify(task_id: str, payload: ReclassifyRequest):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.task_actions.reclassify(task_id, **_options(payload))
        )

    @app.post("/api/tasks/{task_id}/confirm-label")
    def confirm_label(
        task_id: str,
        payload: ExpectedVersionRequest | None = Body(default=None),
    ):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.task_actions.confirm_label(task_id, **_options(payload))
        )

    @app.post("/api/tasks/{task_id}/confirm-reply")
    def confirm_reply(
        task_id: str, payload: ConfirmRequest
    ):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.workflow.confirm_reply(task_id, **_options(payload))
        )

    @app.post("/api/tasks/{task_id}/confirm-forward")
    def confirm_forward(
        task_id: str, payload: ConfirmRequest
    ):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.workflow.confirm_forward(task_id, **_options(payload))
        )

    @app.post("/api/tasks/{task_id}/ignore")
    def ignore(task_id: str, payload: ReasonRequest):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.task_actions.ignore(task_id, **_options(payload))
        )

    @app.post("/api/tasks/{task_id}/manual-review")
    def manual_review(task_id: str, payload: ReasonRequest):
        reject_if_paused()
        _validate_task_id(task_id)
        _task_or_404(view, task_id)
        return _result_or_error(
            services.task_actions.manual_review(task_id, **_options(payload))
        )

    @app.post("/api/feishu/sync")
    def feishu_sync(payload: SyncRequest | None = Body(default=None)):
        reject_if_paused()
        force = False if payload is None else payload.force
        return _result_or_error(services.feishu.check(force=force))

    @app.post("/api/system/health")
    def system_health(
        payload: EmptyRequest | None = Body(default=None),
    ):
        del payload
        return _result_or_error(services.health.run())

    @app.post("/api/system/health/accept")
    def accept_system_health_updates(
        payload: EmptyRequest | None = Body(default=None),
    ):
        del payload
        try:
            return _result_or_error(services.health.accept_verified_updates())
        except (RuntimeError, ValueError, OSError):
            raise HTTPException(
                status_code=409,
                detail="组件验证未通过，未更新版本锁；请检查组件后重试。",
            ) from None

    @app.post("/api/system/open/{target}")
    def open_service_target(
        target: Literal["database", "reply", "contract"],
        payload: EmptyRequest | None = Body(default=None),
    ):
        del payload
        if target not in LOCAL_TARGETS:
            raise HTTPException(status_code=404, detail="该服务入口不存在。")
        try:
            return _result_or_error(launch_service(target))
        except (FileNotFoundError, OSError):
            raise HTTPException(
                status_code=404,
                detail="对应文件或文件夹暂不可用，请先完成组件安装。",
            ) from None

    @app.post("/api/system/pause")
    def system_pause(
        payload: EmptyRequest | None = Body(default=None),
    ) -> dict[str, object]:
        del payload
        if not state.paused():
            state.set_paused(True)
            database.append_audit(action="system_paused", actor="local_user")
        return {"paused": True, "auto_mode": False}

    @app.post("/api/system/resume")
    def system_resume(
        payload: EmptyRequest | None = Body(default=None),
    ) -> dict[str, object]:
        del payload
        if state.paused():
            state.set_paused(False)
            database.append_audit(action="system_resumed", actor="local_user")
        return {"paused": False, "auto_mode": False}

    web_root = Path(__file__).with_name("web")
    app.mount(
        "/assets",
        StaticFiles(directory=web_root),
        name="web-assets",
    )

    @app.get("/", include_in_schema=False)
    def web_home() -> FileResponse:
        return FileResponse(web_root / "index.html")

    return app


app = create_app()


__all__ = [
    "ApiServices",
    "RuntimeState",
    "ServiceUnavailable",
    "create_app",
]
