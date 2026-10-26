#!/usr/bin/env python3
"""Import Markdown into Feishu docx with real table blocks.

This complements feishu_docs.py, whose stable importer writes Markdown as
plain text blocks. This script recognizes simple pipe Markdown tables and
creates Feishu docx table blocks, then fills every cell with text.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
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


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    if len(cells) < 2:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip().replace("<br>", "\n") for cell in stripped.split("|")]


def clean_text(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^\s*[-*]\s+", "- ", line)
    return line


def parse_markdown(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.splitlines()
    items: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line.strip() or line.strip() == "---":
            index += 1
            continue

        if (
            is_table_row(line)
            and index + 1 < len(lines)
            and is_table_separator(lines[index + 1])
        ):
            table_rows = [split_table_row(line)]
            index += 2
            while index < len(lines) and is_table_row(lines[index]):
                row = split_table_row(lines[index])
                table_rows.append(row)
                index += 1
            max_cols = max(len(row) for row in table_rows)
            normalized = [row + [""] * (max_cols - len(row)) for row in table_rows]
            items.append({"type": "table", "rows": normalized})
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            items.append({"type": "heading", "level": level, "text": text})
        else:
            items.append({"type": "text", "text": clean_text(line)})
        index += 1
    return items


def text_block(content: str, block_type: int = 2) -> dict[str, Any]:
    key_by_type = {
        2: "text",
        3: "heading1",
        4: "heading2",
        5: "heading3",
        6: "heading4",
        7: "heading5",
        8: "heading6",
    }
    key = key_by_type.get(block_type, "text")
    return {
        "block_type": block_type,
        key: {"elements": [{"text_run": {"content": content}}]},
    }


def post_children(token: str, document_id: str, parent_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    return fd.http_json(
        "POST",
        f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children",
        token=token,
        query={"document_revision_id": -1},
        payload={"children": children, "index": -1},
    )


def get_children(token: str, document_id: str, parent_id: str) -> list[dict[str, Any]]:
    data = fd.http_json(
        "GET",
        f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children",
        token=token,
    )
    return data.get("data", {}).get("items") or data.get("data", {}).get("children") or []


def patch_text_block(token: str, document_id: str, block_id: str, content: str) -> None:
    fd.http_json(
        "PATCH",
        f"/docx/v1/documents/{document_id}/blocks/{block_id}",
        token=token,
        payload={
            "update_text_elements": {
                "elements": [{"text_run": {"content": content}}],
            }
        },
    )


def create_table(token: str, document_id: str, parent_id: str, rows: list[list[str]]) -> list[str]:
    row_size = len(rows)
    column_size = max(len(row) for row in rows)
    data = post_children(
        token,
        document_id,
        parent_id,
        [
            {
                "block_type": 31,
                "table": {
                    "property": {
                        "row_size": row_size,
                        "column_size": column_size,
                    }
                },
            }
        ],
    )
    table = data.get("data", {}).get("children", [{}])[0]
    cells = table.get("table", {}).get("cells") or table.get("children") or []
    if len(cells) != row_size * column_size:
        raise RuntimeError(f"Unexpected table cell count: got {len(cells)}, expected {row_size * column_size}")
    return cells


def populate_table_cells(token: str, document_id: str, rows: list[list[str]], cells: list[str]) -> None:
    flat = [cell for row in rows for cell in row]
    for cell_id, content in zip(cells, flat):
        if not content:
            content = " "
        existing = get_children(token, document_id, cell_id)
        text_child = next((child for child in existing if child.get("block_type") == 2), None)
        if text_child:
            patch_text_block(token, document_id, text_child["block_id"], content)
        else:
            post_children(token, document_id, cell_id, [text_block(content)])
        time.sleep(0.23)


def import_markdown(source: Path, title: str, document_id: str | None = None) -> dict[str, Any]:
    config = fd.load_config()
    token = fd.get_tenant_access_token(config)
    if document_id is None:
        doc = fd.create_document(token, title, config.get("default_folder_token"))
        document_id = doc["document_id"]
    markdown = source.read_text(encoding="utf-8")
    items = parse_markdown(markdown)

    text_batch: list[dict[str, Any]] = []
    table_count = 0
    text_count = 0

    def flush_text_batch() -> None:
        nonlocal text_batch, text_count
        if not text_batch:
            return
        for offset in range(0, len(text_batch), 50):
            chunk = text_batch[offset : offset + 50]
            post_children(token, document_id, document_id, chunk)
            text_count += len(chunk)
            time.sleep(0.25)
        text_batch = []

    for item in items:
        if item["type"] == "table":
            flush_text_batch()
            cells = create_table(token, document_id, document_id, item["rows"])
            populate_table_cells(token, document_id, item["rows"], cells)
            table_count += 1
            time.sleep(0.25)
        elif item["type"] == "heading":
            block_type = min(8, 2 + int(item["level"]))
            text_batch.append(text_block(item["text"], block_type=block_type))
        else:
            text_batch.append(text_block(item["text"]))

    flush_text_batch()
    return {
        "document_id": document_id,
        "url": fd.document_url(document_id),
        "tables": table_count,
        "text_blocks": text_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--title", required=True)
    parser.add_argument("--document-id", help="Append native table content into an existing docx document.")
    args = parser.parse_args()
    result = import_markdown(Path(args.file).resolve(), args.title, args.document_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
