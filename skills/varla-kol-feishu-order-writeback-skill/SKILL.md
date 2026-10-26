---
name: varla-kol-feishu-order-writeback
description: Record newly created Varla Shopify KOL orders in a user-provided Feishu Base URL. Use when the user asks to upload, write back, sync, or fill KOL order numbers, Code Name, or Impact ID into Feishu after shipment.
compatibility: Windows, Python, Feishu OpenAPI credentials in %USERPROFILE%\\.feishu-docs\\config.json
---

# Varla KOL Feishu Order Writeback

Use this skill after Shopify order creation has been confirmed. The user must provide the current Feishu Base URL and the order results; never hardcode a Base, table, view, app token, or credentials.

## Safe workflow

1. Parse the Feishu URL to obtain the app token and table ID. Keep the view ID only for human reference.
2. Load credentials from `%USERPROFILE%\\.feishu-docs\\config.json` through the local Feishu helper. Never print tokens, app secrets, or raw authorization headers.
3. Read the target table fields and records before mutation. Match each creator by normalized email first; use creator name/handle only as a secondary check.
4. Write the confirmed Shopify `#VARLA...` value to the `订单号` field.
5. Write `Code Name` to `code name` when supplied. If Code Name is absent but an Impact ID is supplied, write the Impact ID to `impact id`. Preserve Impact IDs as text.
6. Set `Contact Status` to `已发货` and update the run date only when the user asked to record shipment.
7. If no unique matching record exists, stop and report the email, candidate records, and missing field. Do not create a duplicate record by guesswork.
8. Re-read every changed record and report the exact creator-to-order mapping.

## Current batch output format

Report:

| KOL | Email | Code Name / Impact ID | Shopify order | Feishu status |
|---|---|---|---|---|

Include a clickable Feishu Base URL and the local workbook/result folder when available.

## Important boundaries

- Do not upload contract attachments unless explicitly requested.
- Do not overwrite an existing non-empty order number without confirming it is the same current order.
- Do not use the Shopify API; Shopify order numbers must come from the confirmed browser workflow.
- Do not include secrets in generated files or logs.
