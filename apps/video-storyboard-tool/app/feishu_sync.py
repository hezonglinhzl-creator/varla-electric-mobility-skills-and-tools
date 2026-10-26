"""Unified Feishu sync entrypoint with separated doc and bitable results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ROOT_DIR
from .exporters import export_feishu_bundle
from .feishu_bitable_sync import sync_bitable, test_bitable_connection
from .feishu_doc_sync import sync_doc, test_doc_connection
from .models import Storyboard, SyncResult


LOG_DIR = ROOT_DIR / "logs"


def result_to_dict(result: SyncResult) -> dict[str, Any]:
    return json.loads(result.model_dump_json())


def write_sync_log(storyboard: Storyboard, local_export: dict[str, Any], doc_result: SyncResult | None, bitable_result: SyncResult | None) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    payload = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "video": storyboard.video_info.file_name,
        "local_export": local_export,
        "feishu_doc_sync": result_to_dict(doc_result) if doc_result else None,
        "feishu_bitable_sync": result_to_dict(bitable_result) if bitable_result else None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def local_export_for_sync(storyboard: Storyboard) -> dict[str, Any]:
    output_dir = ROOT_DIR / "outputs" / storyboard.job_id
    bundle = export_feishu_bundle(storyboard, output_dir, "storyboard")
    return {
        "success": True,
        "files": {key: str(value) for key, value in bundle.items()},
    }


def merge_results(storyboard: Storyboard, target: str, local_export: dict[str, Any], doc_result: SyncResult | None, bitable_result: SyncResult | None) -> SyncResult:
    errors: list[str] = []
    success_count = 0
    failed_count = 0
    ok = True
    doc_url = None
    bitable_url = None

    for name, result in [("飞书文档", doc_result), ("多维表格", bitable_result)]:
        if not result:
            continue
        if result.ok:
            success_count += result.success_count
        else:
            ok = False
            failed_count += result.failed_count or 1
            errors.extend([f"{name}: {error}" for error in result.errors])
        doc_url = doc_url or result.doc_url
        bitable_url = bitable_url or result.bitable_url

    log_path = write_sync_log(storyboard, local_export, doc_result, bitable_result)
    return SyncResult(
        ok=ok,
        success_count=success_count,
        failed_count=failed_count,
        errors=errors,
        doc_url=doc_url,
        bitable_url=bitable_url,
        details={
            "target": target,
            "local_export": local_export,
            "doc": result_to_dict(doc_result) if doc_result else None,
            "bitable": result_to_dict(bitable_result) if bitable_result else None,
            "log_path": str(log_path),
        },
    )


def sync_all(storyboard: Storyboard, target: str = "both", overrides: dict[str, str] | None = None) -> SyncResult:
    local_export = local_export_for_sync(storyboard)
    doc_result: SyncResult | None = None
    bitable_result: SyncResult | None = None

    if target in {"doc", "both"}:
        doc_result = sync_doc(storyboard, overrides)
    if target in {"bitable", "both"}:
        bitable_result = sync_bitable(storyboard, overrides)

    return merge_results(storyboard, target, local_export, doc_result, bitable_result)


__all__ = ["sync_all", "test_doc_connection", "test_bitable_connection"]
