from __future__ import annotations

from copy import copy
from datetime import datetime
from pathlib import Path
import re

import pandas as pd
from openpyxl import load_workbook


REQUIRED_COLUMNS = (
    "name",
    "email",
    "phone",
    "address",
    "city",
    "state",
    "country",
    "zipcode",
    "product",
    "note",
    "tag",
    "shipping_phone_source",
)

OPTIONAL_COLUMNS = (
    "address2",
    "quantity",
    "address_verification_status",
    "address_verification_note",
    "shipping_address_source",
)

ESSENTIAL_FIELDS = (
    "name",
    "email",
    "address",
    "city",
    "state",
    "country",
    "zipcode",
    "product",
)

SUPPORTED_NOTE_CODES = {
    "V-M5S-BK-US": ("M5S", "黑色"),
    "V-M5S-RD-US": ("M5S", "红色"),
    "V-M7S-BK-US": ("M7S", "黑色"),
    "V-M7S-RD-US": ("M7S", "红色"),
}
GIFT_CODE = "VAR-GIFTSET-002"
HELMET_CODE = "A-HELMET-007"
ORDER_CODE_COLUMN = "varla_order_code"
RESULT_COLUMNS = (
    ORDER_CODE_COLUMN,
    "shopify_order_status",
    "shopify_order_url",
    "draft_order_code",
    "shopify_created_at",
    "feishu_sync_status",
)


class OrderDataError(ValueError):
    """Raised when the workbook cannot provide one safe test order."""


def _clean_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_us_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise OrderDataError("美国电话号码必须是 10 位数字，不带 +1")
    return digits


def validate_note(note: str) -> tuple[str, str]:
    """Validate the exact two-line model/color and gift code convention."""

    lines = [line.strip() for line in note.splitlines() if line.strip()]
    if len(lines) not in (2, 3):
        raise OrderDataError(
            "Note 必须正好两行：第一行为车型颜色码，第二行为 VAR-GIFTSET-002"
        )
    sku_code, gift_code = lines[:2]
    if sku_code not in SUPPORTED_NOTE_CODES:
        supported = ", ".join(SUPPORTED_NOTE_CODES)
        raise OrderDataError(f"不支持的车型颜色码 {sku_code}；可用值：{supported}")
    if gift_code != GIFT_CODE:
        raise OrderDataError(f"Note 第二行必须是 {GIFT_CODE}")
    if len(lines) == 3 and lines[2] != HELMET_CODE:
        raise OrderDataError(f"Note 第三行仅支持头盔 SKU: {HELMET_CODE}")
    return sku_code, gift_code


def validate_note(note: str) -> tuple[str, str]:
    """Validate one or two vehicle codes followed by the required gift code."""

    lines = [line.strip() for line in note.splitlines() if line.strip()]
    if len(lines) not in (2, 3):
        raise OrderDataError("Note must include one/two vehicle codes and VAR-GIFTSET-002")
    if len(lines) == 3 and lines[1] == GIFT_CODE and lines[2] == HELMET_CODE:
        if lines[0] not in SUPPORTED_NOTE_CODES:
            raise OrderDataError(f"不支持的车型颜色码: {lines[0]}")
        return lines[0], GIFT_CODE
    vehicle_codes, gift_code = lines[:-1], lines[-1]
    unsupported = [code for code in vehicle_codes if code not in SUPPORTED_NOTE_CODES]
    if unsupported:
        supported = ", ".join(SUPPORTED_NOTE_CODES)
        raise OrderDataError(f"不支持的车型颜色码: {unsupported[0]}; allowed: {supported}")
    if gift_code != GIFT_CODE:
        raise OrderDataError(f"Final Note line must be {GIFT_CODE}")
    return vehicle_codes[0], gift_code


def read_first_order(path: str | Path) -> dict[str, str]:
    """Read the first non-empty order and return the required string dictionary."""

    workbook_path = Path(path)
    if not workbook_path.exists():
        raise OrderDataError(f"找不到 Excel 文件: {workbook_path}")

    try:
        frame = pd.read_excel(
            workbook_path,
            dtype=str,
            keep_default_na=False,
            engine="openpyxl",
        )
    except Exception as exc:
        raise OrderDataError(f"Excel 读取失败: {exc}") from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise OrderDataError(f"Excel 缺少字段: {', '.join(missing)}")

    selected: dict[str, str] | None = None
    for _, row in frame.iterrows():
        candidate = {
            column: _clean_value(row[column]) for column in REQUIRED_COLUMNS
        }
        candidate.update(
            {
                column: _clean_value(row[column])
                if column in frame.columns
                else ""
                for column in OPTIONAL_COLUMNS
            }
        )
        has_order_data = any(candidate.values())
        if has_order_data:
            quantity = candidate.get("quantity", "") or "1"
            if not quantity.isdigit() or int(quantity) < 1:
                raise OrderDataError("quantity must be a positive integer")
            candidate["quantity"] = quantity
        already_created = (
            ORDER_CODE_COLUMN in frame.columns
            and _clean_value(row[ORDER_CODE_COLUMN])
        )
        provisional_created = (
            "draft_order_code" in frame.columns
            and "shopify_order_status" in frame.columns
            and bool(_clean_value(row["draft_order_code"]))
            and _clean_value(row["shopify_order_status"]).casefold()
            == "paid / unfulfilled"
        )
        if any(candidate.values()) and not already_created and not provisional_created:
            selected = candidate
            break

    if selected is None:
        raise OrderDataError("Excel 中没有尚未创建的有效订单")

    blank_essentials = [field for field in ESSENTIAL_FIELDS if not selected[field]]
    if blank_essentials:
        raise OrderDataError(
            f"第一条有效订单缺少必填内容: {', '.join(blank_essentials)}"
        )

    validate_note(selected["note"])
    if selected["shipping_phone_source"].strip().upper() not in {
        "CONTRACT",
        "CREATOR_MESSAGE",
    }:
        raise OrderDataError(
            "phone source must be CONTRACT or CREATOR_MESSAGE; missing or inferred phones stop shipment"
        )
    if selected.get("shipping_address_source", "").strip().upper() not in {
        "CONTRACT_EXACT",
        "CREATOR_MESSAGE",
        "CONTRACT_AND_CREATOR",
    }:
        raise OrderDataError(
            "address source must be CONTRACT_EXACT, CREATOR_MESSAGE, or CONTRACT_AND_CREATOR; inferred map addresses stop shipment"
        )
    if selected["country"].casefold() in (
        "united states",
        "united states of america",
        "usa",
        "us",
    ):
        selected["phone"] = normalize_us_phone(selected["phone"])
    return selected


def save_varla_order_code(
    path: str | Path,
    *,
    name: str,
    email: str,
    order_code: str,
) -> int:
    """Write a Shopify order code back to the one row matching name + email."""

    return save_order_result(
        path,
        name=name,
        email=email,
        order_code=order_code,
    )


def save_order_result(
    path: str | Path,
    *,
    name: str,
    email: str,
    order_code: str,
    order_status: str = "",
    order_url: str = "",
    draft_order_code: str = "",
    created_at: str = "",
    feishu_sync_status: str = "",
) -> int:
    """Write the Shopify result to the unique matching source row."""

    if not re_fullmatch_varla_code(order_code):
        raise OrderDataError(f"订单号格式不正确: {order_code}")

    workbook_path = Path(path)
    if not workbook_path.exists():
        raise OrderDataError(f"找不到 Excel 文件: {workbook_path}")

    workbook = load_workbook(workbook_path)
    sheet = workbook.active
    headers = {
        _clean_value(cell.value): cell.column
        for cell in sheet[1]
        if _clean_value(cell.value)
    }
    for required in ("name", "email"):
        if required not in headers:
            raise OrderDataError(f"Excel 缺少字段: {required}")

    normalized_name = " ".join(name.casefold().split())
    normalized_email = email.strip().casefold()
    matched_rows = []
    for row_index in range(2, sheet.max_row + 1):
        row_name = " ".join(
            _clean_value(sheet.cell(row_index, headers["name"]).value)
            .casefold()
            .split()
        )
        row_email = _clean_value(
            sheet.cell(row_index, headers["email"]).value
        ).casefold()
        if row_name == normalized_name and row_email == normalized_email:
            matched_rows.append(row_index)

    if len(matched_rows) != 1 and ORDER_CODE_COLUMN in headers:
        idempotent_rows = [
            row_index
            for row_index in matched_rows
            if _clean_value(
                sheet.cell(row_index, headers[ORDER_CODE_COLUMN]).value
            ).casefold()
            == order_code.casefold()
        ]
        pending_rows = [
            row_index
            for row_index in matched_rows
            if not _clean_value(
                sheet.cell(row_index, headers[ORDER_CODE_COLUMN]).value
            )
        ]
        if len(idempotent_rows) == 1:
            matched_rows = idempotent_rows
        elif len(pending_rows) == 1:
            matched_rows = pending_rows

    if len(matched_rows) != 1:
        raise OrderDataError(
            "订单号回写要求姓名+邮箱唯一匹配，"
            f"实际匹配到 {len(matched_rows)} 行"
        )

    row_index = matched_rows[0]
    for column_name in RESULT_COLUMNS:
        if column_name in headers:
            continue
        target_column = sheet.max_column + 1
        source_header = sheet.cell(1, target_column - 1)
        target_header = sheet.cell(1, target_column)
        if source_header.has_style:
            target_header._style = copy(source_header._style)
        target_header.font = copy(source_header.font)
        target_header.fill = copy(source_header.fill)
        target_header.border = copy(source_header.border)
        target_header.alignment = copy(source_header.alignment)
        target_header.protection = copy(source_header.protection)
        target_header.number_format = source_header.number_format
        target_header.value = column_name
        sheet.column_dimensions[target_header.column_letter].width = max(
            20,
            sheet.column_dimensions[source_header.column_letter].width or 0,
        )
        headers[column_name] = target_column

    current = _clean_value(
        sheet.cell(row_index, headers[ORDER_CODE_COLUMN]).value
    )
    if current and current != order_code:
        raise OrderDataError(
            f"该行已有不同订单号 {current}，为避免覆盖已停止回写"
        )

    values = {
        ORDER_CODE_COLUMN: order_code,
        "shopify_order_status": order_status,
        "shopify_order_url": order_url,
        "draft_order_code": draft_order_code,
        "shopify_created_at": created_at
        or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # 飞书导入由独立 skill 处理；本工具只保留字段，不预设同步状态。
        "feishu_sync_status": feishu_sync_status,
    }
    for column_name, value in values.items():
        target_column = headers[column_name]
        target = sheet.cell(row_index, target_column)
        if not target.has_style and target_column > 1:
            source = sheet.cell(row_index, target_column - 1)
            if source.has_style:
                target._style = copy(source._style)
        target.number_format = "@"
        if value or not _clean_value(target.value):
            target.value = value

    workbook.save(workbook_path)
    return row_index


def save_provisional_order_result(
    path: str | Path,
    *,
    name: str,
    email: str,
    draft_order_code: str,
    order_status: str,
    order_url: str,
    created_at: str = "",
) -> int:
    """Record a confirmed Shopify order when the UI exposes only a #D code.

    The canonical #VARLA field remains blank so later reconciliation can fill it,
    but the row is no longer eligible for re-submission.
    """

    if not re.fullmatch(r"#D\d+", draft_order_code.strip(), re.IGNORECASE):
        raise OrderDataError(f"Invalid Shopify draft/order reference: {draft_order_code}")
    if order_status.strip().casefold() != "paid / unfulfilled":
        raise OrderDataError("Provisional result requires confirmed Paid / Unfulfilled status")

    workbook_path = Path(path)
    workbook = load_workbook(workbook_path)
    sheet = workbook.active
    headers = {
        _clean_value(cell.value): cell.column
        for cell in sheet[1]
        if _clean_value(cell.value)
    }
    for column_name in RESULT_COLUMNS:
        if column_name in headers:
            continue
        target_column = sheet.max_column + 1
        source_header = sheet.cell(1, target_column - 1)
        target_header = sheet.cell(1, target_column)
        if source_header.has_style:
            target_header._style = copy(source_header._style)
        target_header.font = copy(source_header.font)
        target_header.fill = copy(source_header.fill)
        target_header.border = copy(source_header.border)
        target_header.alignment = copy(source_header.alignment)
        target_header.protection = copy(source_header.protection)
        target_header.number_format = source_header.number_format
        target_header.value = column_name
        headers[column_name] = target_column

    normalized_name = " ".join(name.casefold().split())
    normalized_email = email.strip().casefold()
    matched_rows = [
        row_index
        for row_index in range(2, sheet.max_row + 1)
        if " ".join(
            _clean_value(sheet.cell(row_index, headers["name"]).value)
            .casefold()
            .split()
        )
        == normalized_name
        and _clean_value(sheet.cell(row_index, headers["email"]).value).casefold()
        == normalized_email
    ]
    if len(matched_rows) != 1:
        raise OrderDataError(
            f"Provisional writeback requires one identity row; found {len(matched_rows)}"
        )
    row_index = matched_rows[0]
    if _clean_value(sheet.cell(row_index, headers[ORDER_CODE_COLUMN]).value):
        raise OrderDataError("Refusing to replace an existing #VARLA code")

    values = {
        "shopify_order_status": order_status,
        "shopify_order_url": order_url,
        "draft_order_code": draft_order_code.upper(),
        "shopify_created_at": created_at
        or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    for column_name, value in values.items():
        target = sheet.cell(row_index, headers[column_name])
        target.number_format = "@"
        target.value = value
    workbook.save(workbook_path)
    return row_index


def re_fullmatch_varla_code(value: str) -> bool:
    return re.fullmatch(r"#VARLA\d+", value.strip(), re.IGNORECASE) is not None
