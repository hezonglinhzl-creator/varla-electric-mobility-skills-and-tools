"""Feishu Docx sync using the local native table payload."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any

from .feishu_common import FeishuApiError, FeishuClient, extract_docx_token, extract_wiki_token, text_block
from .models import TABLE_FIELDS, Storyboard, SyncResult


def resolve_document(client: FeishuClient) -> tuple[str, str, dict[str, Any]]:
    config = client.config
    doc_id = config.get("doc_id") or extract_docx_token(config.get("doc_url"))
    if doc_id:
        return doc_id, config.get("doc_url") or f"https://m9kzgsiucj.feishu.cn/docx/{doc_id}", {"source": "docx"}

    wiki_url = config.get("wiki_parent_url") or config.get("doc_url")
    wiki_token = extract_wiki_token(wiki_url) or config.get("wiki_parent_node_token")
    if not wiki_token:
        raise FeishuApiError("文档 ID / URL 解析失败或文档不存在")
    node_data = client.request("GET", "/wiki/v2/spaces/get_node", params={"token": wiki_token})
    node = node_data.get("data", {}).get("node", {})
    if node.get("obj_type") != "docx":
        raise FeishuApiError(f"这是知识库链接，但节点不是 docx：{node.get('obj_type')}", raw_error=node_data)
    obj_token = node.get("obj_token")
    if not obj_token:
        raise FeishuApiError("知识库 wiki token 转换失败，未拿到 obj_token", raw_error=node_data)
    return obj_token, wiki_url, {"source": "wiki", "wiki_token": wiki_token, "node": node}


def get_root_children(client: FeishuClient, document_id: str) -> list[dict[str, Any]]:
    data = client.request("GET", f"/docx/v1/documents/{document_id}/blocks/{document_id}/children")
    return data.get("data", {}).get("items") or data.get("data", {}).get("children") or []


def post_children(
    client: FeishuClient,
    document_id: str,
    parent_id: str,
    children: list[dict[str, Any]],
    *,
    index: int = -1,
) -> dict[str, Any]:
    return client.request(
        "POST",
        f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children",
        params={"document_revision_id": -1},
        payload={"children": children, "index": index},
    )


def get_children(client: FeishuClient, document_id: str, parent_id: str) -> list[dict[str, Any]]:
    data = client.request("GET", f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children")
    return data.get("data", {}).get("items") or data.get("data", {}).get("children") or []


def delete_children_range(client: FeishuClient, document_id: str, parent_id: str, start_index: int, end_index: int) -> None:
    client.request(
        "DELETE",
        f"/docx/v1/documents/{document_id}/blocks/{parent_id}/children/batch_delete",
        params={"document_revision_id": -1},
        payload={"start_index": start_index, "end_index": end_index},
    )


def block_text_content(block: dict[str, Any]) -> str:
    text = block.get("text") or {}
    elements = text.get("elements") or []
    return "".join(str(element.get("text_run", {}).get("content", "")) for element in elements).strip()


def delete_empty_text_children(client: FeishuClient, document_id: str, parent_id: str) -> int:
    removed = 0
    children = get_children(client, document_id, parent_id)
    for index in range(len(children) - 1, -1, -1):
        child = children[index]
        if child.get("block_type") == 2 and not block_text_content(child):
            delete_children_range(client, document_id, parent_id, index, index + 1)
            removed += 1
            time.sleep(0.12)
    return removed


def patch_text_block(client: FeishuClient, document_id: str, block_id: str, content: str) -> None:
    client.request(
        "PATCH",
        f"/docx/v1/documents/{document_id}/blocks/{block_id}",
        params={"document_revision_id": -1},
        payload={
            "update_text_elements": {
                "elements": [{"text_run": {"content": content}}],
            }
        },
    )


def fill_text_cell(client: FeishuClient, document_id: str, cell_id: str, content: str) -> None:
    clean = clean_cell_text(content)
    if not clean:
        return
    existing = get_children(client, document_id, cell_id)
    text_child = next((child for child in existing if child.get("block_type") == 2), None)
    if text_child:
        patch_text_block(client, document_id, block_id(text_child), clean)
    else:
        post_children(client, document_id, cell_id, [text_block(clean)])


def block_id(block: Any) -> str:
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        return str(block.get("block_id") or block.get("blockId") or block.get("id") or "")
    return ""


def upload_image_to_block(client: FeishuClient, image_block_id: str, frame_path: str) -> str:
    frame = Path(frame_path)
    if not image_block_id or not frame.exists():
        return ""
    mime = mimetypes.guess_type(frame.name)[0] or "image/jpeg"
    with frame.open("rb") as file:
        data = client.request(
            "POST",
            "/drive/v1/medias/upload_all",
            payload={
                "file_name": frame.name,
                "parent_type": "docx_image",
                "parent_node": image_block_id,
                "size": str(frame.stat().st_size),
            },
            files={"file": (frame.name, file, mime)},
            retries=1,
        )
    return str(data.get("data", {}).get("file_token") or "")


def replace_image_block(client: FeishuClient, document_id: str, image_block_id: str, file_token: str) -> None:
    if not image_block_id or not file_token:
        raise FeishuApiError("图片上传后未拿到 file_token，无法替换图片块")
    client.request(
        "PATCH",
        f"/docx/v1/documents/{document_id}/blocks/{image_block_id}",
        params={"document_revision_id": -1},
        payload={"replace_image": {"token": file_token}},
        retries=1,
    )


def fill_image_cell(client: FeishuClient, document_id: str, cell_id: str, frame_path: str) -> None:
    if not frame_path or not Path(frame_path).exists():
        return
    try:
        delete_empty_text_children(client, document_id, cell_id)
    except FeishuApiError:
        existing = get_children(client, document_id, cell_id)
        text_child = next((child for child in existing if child.get("block_type") == 2), None)
        if text_child:
            patch_text_block(client, document_id, block_id(text_child), "")
    data = post_children(client, document_id, cell_id, [{"block_type": 27, "image": {}}], index=0)
    children = data.get("data", {}).get("children", [])
    image_block_id = block_id(children[0]) if children else ""
    if not image_block_id:
        raise FeishuApiError("图片块创建失败，无法上传静帧", raw_error=data)
    file_token = upload_image_to_block(client, image_block_id, frame_path)
    replace_image_block(client, document_id, image_block_id, file_token)


def table_block(row_size: int, column_size: int) -> dict[str, Any]:
    return {
        "block_type": 31,
        "table": {
            "property": {
                "row_size": row_size,
                "column_size": column_size,
            }
        },
    }


def table_cells(table: dict[str, Any], row_size: int, column_size: int, raw_error: dict[str, Any]) -> list[Any]:
    cells = table.get("table", {}).get("cells") or table.get("children") or []
    expected = row_size * column_size
    if len(cells) != expected:
        raise FeishuApiError(f"父块不存在或 table cell 数量异常：got {len(cells)}, expected {expected}", raw_error=raw_error)
    return cells


def fill_table_cells(client: FeishuClient, document_id: str, rows: list[list[dict[str, str]]], cells: list[Any]) -> None:
    column_size = len(TABLE_FIELDS)
    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            cell_id = block_id(cells[row_index * column_size + col_index])
            if cell.get("type") == "image":
                fill_image_cell(client, document_id, cell_id, cell.get("path", ""))
            else:
                fill_text_cell(client, document_id, cell_id, cell.get("text", ""))
            time.sleep(0.12)


def create_native_table(client: FeishuClient, document_id: str, rows: list[list[dict[str, str]]], index: int = -1) -> None:
    row_size = len(rows)
    column_size = len(TABLE_FIELDS)
    data = post_children(
        client,
        document_id,
        document_id,
        [table_block(row_size, column_size)],
        index=index,
    )
    table = data.get("data", {}).get("children", [{}])[0]
    fill_table_cells(client, document_id, rows, table_cells(table, row_size, column_size, data))


def create_native_tables(
    client: FeishuClient,
    document_id: str,
    tables: list[list[list[dict[str, str]]]],
    index: int = -1,
) -> None:
    if not tables:
        return
    column_size = len(TABLE_FIELDS)
    data = post_children(
        client,
        document_id,
        document_id,
        [table_block(len(rows), column_size) for rows in tables],
        index=index,
    )
    created_tables = data.get("data", {}).get("children", [])
    if len(created_tables) != len(tables):
        raise FeishuApiError(
            f"批量表格创建数量异常：got {len(created_tables)}, expected {len(tables)}",
            raw_error=data,
        )
    for rows, table in zip(tables, created_tables):
        cells = table_cells(table, len(rows), column_size, data)
        fill_table_cells(client, document_id, rows, cells)


def clean_cell_text(text: str) -> str:
    return " ".join(str(text or "").split())


def text_cell(text: str) -> dict[str, str]:
    return {"type": "text", "text": clean_cell_text(text)}


def image_cell(path: str) -> dict[str, str]:
    return {"type": "image", "path": path or ""}


def storyboard_rows(storyboard: Storyboard) -> list[list[dict[str, str]]]:
    rows = [[text_cell(field) for field in TABLE_FIELDS]]
    for shot in storyboard.shots:
        rows.append(
            [
                text_cell(shot.shot_id),
                text_cell(shot.shot_size),
                text_cell(shot.camera_method),
                image_cell(shot.frame_path),
                text_cell(shot.visual_description),
                text_cell(shot.notes),
                text_cell(shot.dialogue_cn),
                text_cell(shot.dialogue_en),
            ]
        )
    return rows


def storyboard_row_chunks(storyboard: Storyboard, max_shots_per_table: int = 6) -> list[list[list[dict[str, str]]]]:
    header = [[text_cell(field) for field in TABLE_FIELDS]]
    chunks: list[list[list[dict[str, str]]]] = []
    shot_rows = storyboard_rows(storyboard)[1:]
    for start in range(0, len(shot_rows), max_shots_per_table):
        chunks.append(header + shot_rows[start : start + max_shots_per_table])
    return chunks or [header]


def sync_doc(storyboard: Storyboard, overrides: dict[str, str] | None = None) -> SyncResult:
    client = FeishuClient(overrides)
    try:
        document_id, url, meta = resolve_document(client)
        children = get_root_children(client, document_id)
        if children is None:
            raise FeishuApiError("获取文档块失败，不继续写入")
        append_index = len(children)
        rows = storyboard_rows(storyboard)
        used_fallback_chunks = 0
        chunks = storyboard_row_chunks(storyboard)
        if len(chunks) > 1:
            post_children(
                client,
                document_id,
                document_id,
                [
                    text_block(storyboard.video_info.file_name, 4),
                ],
                index=append_index,
            )
            create_native_tables(client, document_id, chunks, index=-1)
            used_fallback_chunks = len(chunks)
        else:
            try:
                create_native_table(client, document_id, rows, index=append_index)
            except FeishuApiError as exc:
                if str(exc.code) != "1770001":
                    raise
                post_children(
                    client,
                    document_id,
                    document_id,
                    [
                        text_block(storyboard.video_info.file_name, 4),
                    ],
                    index=append_index,
                )
                create_native_tables(client, document_id, chunks, index=-1)
                used_fallback_chunks = len(chunks)
            else:
                post_children(
                    client,
                    document_id,
                    document_id,
                    [
                        text_block(storyboard.video_info.file_name, 4),
                    ],
                    index=append_index,
                )
        result = SyncResult(ok=True, success_count=len(storyboard.shots), doc_url=url)
        result.details = {
            "document_id": document_id,
            "document_meta": meta,
            "native_table": True,
            "single_table": used_fallback_chunks == 0,
            "fallback_chunks": used_fallback_chunks,
            "append_only": True,
            "append_index": append_index,
            "existing_block_count_before_append": len(children),
        }
        return result
    except FeishuApiError as exc:
        return SyncResult(ok=False, failed_count=1, errors=[str(exc)], details={"doc": exc.to_dict()})
    except Exception as exc:
        return SyncResult(ok=False, failed_count=1, errors=[str(exc)], details={"doc": {"message": str(exc)}})


def test_doc_connection(overrides: dict[str, str] | None = None) -> dict[str, Any]:
    client = FeishuClient(overrides)
    checks: dict[str, Any] = {"app_id_loaded": bool(client.config.get("app_id"))}
    try:
        client.tenant_access_token()
        checks["tenant_access_token"] = True
        document_id, url, meta = resolve_document(client)
        checks.update({"document_id": document_id, "doc_url": url, "document_meta": meta})
        children = get_root_children(client, document_id)
        checks["root_block_exists"] = True
        checks["block_count"] = len(children)
        checks["editable_check"] = "可读取；写入权限会在同步时验证"
        return {"ok": True, "checks": checks}
    except FeishuApiError as exc:
        checks["error"] = exc.to_dict()
        return {"ok": False, "checks": checks}
    except Exception as exc:
        checks["error"] = {"message": str(exc)}
        return {"ok": False, "checks": checks}
