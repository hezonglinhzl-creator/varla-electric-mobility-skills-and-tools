"""Feishu Bitable sync using storyboard_payload rows."""

from __future__ import annotations

from typing import Any

from .exporters import feishu_payload_rows
from .feishu_common import FeishuApiError, FeishuClient, parse_bitable_url
from .models import FEISHU_FIELD_MAP, FEISHU_TABLE_FIELDS, Storyboard, SyncResult


def resolve_bitable(client: FeishuClient) -> tuple[str, str, dict[str, str]]:
    parsed = parse_bitable_url(client.config.get("bitable_url"))
    app_token = client.config.get("bitable_app_token") or parsed.get("app_token", "")
    table_id = client.config.get("bitable_table_id") or parsed.get("table_id", "")
    if not app_token:
        raise FeishuApiError("缺少 FEISHU_BITABLE_APP_TOKEN 或 FEISHU_BITABLE_URL")
    if not table_id:
        raise FeishuApiError("缺少 FEISHU_BITABLE_TABLE_ID，不能把 document_id 当成 table_id")
    return app_token, table_id, parsed


def list_tables(client: FeishuClient, app_token: str) -> list[dict[str, Any]]:
    data = client.request("GET", f"/bitable/v1/apps/{app_token}/tables")
    return data.get("data", {}).get("items", [])


def list_fields(client: FeishuClient, app_token: str, table_id: str) -> list[dict[str, Any]]:
    data = client.request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")
    return data.get("data", {}).get("items", [])


def ensure_fields(client: FeishuClient, app_token: str, table_id: str) -> dict[str, Any]:
    fields = list_fields(client, app_token, table_id)
    existing = {field.get("field_name"): field for field in fields}
    created: list[str] = []
    for name in FEISHU_TABLE_FIELDS:
        if name in existing:
            continue
        client.request(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            payload={"field_name": name, "type": 1},
        )
        created.append(name)
    return {"existing": list(existing), "created": created}


def build_records(storyboard: Storyboard) -> list[dict[str, Any]]:
    records = []
    for row in feishu_payload_rows(storyboard):
        fields = {feishu_name: row[key] for key, feishu_name in FEISHU_FIELD_MAP.items()}
        records.append({"fields": fields})
    return records


def sync_bitable(storyboard: Storyboard, overrides: dict[str, str] | None = None) -> SyncResult:
    client = FeishuClient(overrides)
    try:
        app_token, table_id, parsed = resolve_bitable(client)
        tables = list_tables(client, app_token)
        if table_id not in {table.get("table_id") for table in tables}:
            raise FeishuApiError(
                "table_id 不存在，请检查多维表格 URL 或 FEISHU_BITABLE_TABLE_ID",
                raw_error={"app_token": app_token, "table_id": table_id, "tables": tables},
            )
        field_status = ensure_fields(client, app_token, table_id)
        records = build_records(storyboard)
        for offset in range(0, len(records), 500):
            client.request(
                "POST",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                payload={"records": records[offset : offset + 500]},
            )
        result = SyncResult(ok=True, success_count=len(records), bitable_url=client.config.get("bitable_url") or None)
        result.details = {
            "app_token": app_token,
            "table_id": table_id,
            "parsed": parsed,
            "fields": field_status,
        }
        return result
    except FeishuApiError as exc:
        return SyncResult(ok=False, failed_count=1, errors=[str(exc)], details={"bitable": exc.to_dict()})
    except Exception as exc:
        return SyncResult(ok=False, failed_count=1, errors=[str(exc)], details={"bitable": {"message": str(exc)}})


def test_bitable_connection(overrides: dict[str, str] | None = None) -> dict[str, Any]:
    client = FeishuClient(overrides)
    checks: dict[str, Any] = {"app_id_loaded": bool(client.config.get("app_id"))}
    try:
        client.tenant_access_token()
        checks["tenant_access_token"] = True
        app_token, table_id, parsed = resolve_bitable(client)
        checks.update({"app_token": app_token, "table_id": table_id, "parsed": parsed})
        tables = list_tables(client, app_token)
        checks["app_exists"] = True
        checks["table_exists"] = table_id in {table.get("table_id") for table in tables}
        if checks["table_exists"]:
            fields = list_fields(client, app_token, table_id)
            field_names = {field.get("field_name") for field in fields}
            checks["fields"] = sorted(field_names)
            checks["missing_fields"] = [name for name in FEISHU_TABLE_FIELDS if name not in field_names]
        return {"ok": bool(checks.get("table_exists")), "checks": checks}
    except FeishuApiError as exc:
        checks["error"] = exc.to_dict()
        return {"ok": False, "checks": checks}
    except Exception as exc:
        checks["error"] = {"message": str(exc)}
        return {"ok": False, "checks": checks}
