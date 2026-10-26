from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FEISHU_DOCS = ROOT / "scripts" / "feishu_docs.py"


def load_feishu_docs():
    spec = importlib.util.spec_from_file_location("feishu_docs", FEISHU_DOCS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {FEISHU_DOCS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fd = load_feishu_docs()


def get_children(token: str, document_id: str, parent_id: str) -> list[dict[str, Any]]:
    data = fd.http_json(
        "GET",
        f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children",
        token=token,
    )
    return data.get("data", {}).get("items") or data.get("data", {}).get("children") or []


def text_contents(items: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in items:
        if item.get("block_type") != 2:
            continue
        elements = (item.get("text") or {}).get("elements") or []
        for element in elements:
            run = element.get("text_run") or {}
            values.append(str(run.get("content") or ""))
    return values


def verify(document_id: str, sample_tables: int) -> dict[str, Any]:
    token = fd.get_tenant_access_token(fd.load_config())
    children = get_children(token, document_id, document_id)
    tables = [child for child in children if child.get("block_type") == 31]
    bad_cells: list[dict[str, Any]] = []
    checked_cells = 0

    for table in tables[:sample_tables]:
        cells = table.get("table", {}).get("cells") or table.get("children") or []
        for cell_id in cells:
            cell_children = get_children(token, document_id, cell_id)
            texts = text_contents(cell_children)
            checked_cells += 1
            if len(cell_children) != 1 or not "".join(texts).strip():
                bad_cells.append(
                    {
                        "cell_id": cell_id,
                        "child_count": len(cell_children),
                        "texts": texts,
                    }
                )

    return {
        "document_id": document_id,
        "children": len(children),
        "table_blocks": len(tables),
        "checked_cells": checked_cells,
        "bad_cells": bad_cells[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--sample-tables", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(verify(args.document_id, args.sample_tables), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
