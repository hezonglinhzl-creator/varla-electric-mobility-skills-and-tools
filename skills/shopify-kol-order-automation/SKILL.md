---
name: shopify-kol-order-automation
description: Operate the existing Varla Shopify KOL/KOC order workflow from contracts, screenshots, Word, PDF, or Excel through address verification, AdsPower/Playwright browser entry, paid order creation, and #VARLA writeback. Use this skill whenever the user asks to 整理KOL发货资料, Shopify自动发货, 创建KOL订单, 校对美国收货地址, 批量逐单发货, 重发取消订单, or save Shopify/VARLA results to XLSX. Always use it for the Varla `shopify_order_bot` workflow even when the request is brief such as “开始发货” or “写入表格”.
---

## Portable distribution paths / 完整包程序位置

Before running a program, read `PACKAGE-LOCATION.json` beside this installed SKILL.md.
Its `apps` object maps each bundled program name to the real extracted directory;
`package_root` points to the complete bundle. Use those paths first. Absolute paths
in older examples below are historical examples, not automatic defaults.
If this file is missing or the bundle was moved, rerun the complete project's
install.ps1 to refresh the mapping. Keep the extracted program directory.
Never treat YOUR_* placeholders as configured credentials or resource IDs.

运行程序前先读取本 SKILL.md 旁边的 `PACKAGE-LOCATION.json`：`apps` 是实际程序目录，
`package_root` 是完整包位置。下文旧电脑绝对路径只作为历史示例，不能自动照用。
缺少映射或完整包搬家后，重新运行完整包 install.ps1；保留解压后的程序目录。
YOUR_* 占位符不代表已配置账号或资源；真实写入前必须使用自己的授权和目标链接。


# shopify自动发货

Use the existing project at:

`C:\Users\<your-user>\Documents\电摩项目\shopify_order_bot`

Do not recreate the bot, copy credentials into this Skill, or call Shopify APIs. Operate Shopify
through the existing AdsPower persistent browser and Playwright UI automation only. If the user
explicitly asks for Feishu writeback after an order, use the separate `飞书codex本地链接skill` skill
and its local Python OpenAPI tools; do not use `lark-cli`.

## Read supporting rules

Before editing an order workbook or submitting an order, read:

- [references/data-contract.md](references/data-contract.md) for fields, normalization, vehicle codes, and writeback rules.
- [references/operating-checklist.md](references/operating-checklist.md) for browser sequencing, safety gates, and recovery.
- [references/contract-extraction.md](references/contract-extraction.md) for quickly locating email, shipping information, Code Name, and Impact ID in Varla contracts.
- [references/adspower-runtime.md](references/adspower-runtime.md) before any browser action, so the existing AdsPower profile is started and attached correctly.
- [references/shipping-evidence-gate.md](references/shipping-evidence-gate.md) before staging any shipment. This gate is mandatory.

## Choose the current phase

Infer the phase from the user's latest instruction and the current workbook/browser state.
Do not restart completed phases.

1. **Prepare** — extract every supplied person's data before opening Shopify.
2. **Review** — verify addresses and show the staged workbook; do not submit.
3. **Submit** — create real orders only after explicit authorization in the current conversation.
4. **Reconcile** — read current Shopify results and align them to Excel by email, never by row position alone.

Explicit submit authorization includes direct phrases such as “开始发货”, “直接提交”,
“创建订单”, or “继续发剩下的”. A request to “整理”, “拆解”, “导入 Excel”, “给我看表格”,
or “测试填写” is not submit authorization.

## Fast continuation in a new chat

This skill is the delivery source of truth. A new chat should inspect the current workbook and
live Shopify/AdsPower page, then resume from the first missing field rather than replaying history.

For delivery-stage contract extraction, use this fixed read-only template when a current creator-specific contract is not supplied:

`C:\Users\<your-user>\Downloads\合作合同\2026-08-06_Varla_KOL_Agreement_M7S_creator@example.com.docx`

Never modify, rename, move, or delete this template. Generate a separate creator-specific contract copy before extracting shipping data. Each copy must be independently customized and must not contain an `Impact ID Number` field; if shipping extraction requires an impact ID, obtain it from the approved source record rather than adding it to the contract.

- US phones are stored in Excel as 10 digits only; Shopify may display `+1` after save.
- The canonical order reference is `#VARLA...`, not a Shopify UI tag. If Shopify has created a paid/unfulfilled order but exposes only `#D...`, treat it as a confirmed provisional result: preserve `#D` in `draft_order_code`, status, URL, and timestamp; leave `varla_order_code` blank for later reconciliation. Never retry submission to chase a `#VARLA` code.
- Notes contain the vehicle code plus `VAR-GIFTSET-002`; order tag is `KOL-PETER`.
- Never use billing data, `View map`, old test customers, or historical canceled orders as input.
- Do not refresh a live Shopify draft. Repair only the first unfinished field.
- The KOL command center may route an order/logistics task here, but it must not create a Shopify order from email classification alone. A reviewed contract, confirmed recipient/shipping data, model/quantity, and explicit current submit authorization remain required.
- Shopify/AdsPower reauthentication is independent from Gmail OAuth and reply-assistant version checks. Report the failing component without invalidating the others.

## Phase 1: Prepare all people first

1. Inspect all source contracts/images/documents in the supplied folder.
2. Locate the creator email, Shipping Information block, Code Name, and Impact ID using the contract anchors reference.
3. Create the address evidence comparison before staging: contract versus direct creator message. Compare street number/name, unit, city, state, ZIP, and country one by one. A `To be confirmed` label may be ignored only when the same source line supplies a complete later value; otherwise it is missing data. Do not open Shopify until every component agrees.
4. Treat a missing phone as a hard stop. Only a number explicitly present in the current contract or direct creator message may be used; never borrow, infer, search for, or reuse a historical customer phone.
5. Extract the entire batch before operating Shopify. Do not alternate contract parsing and order creation.
6. Populate `KOL_order.xlsx` with structured fields from the data contract, including Code Name and Impact ID when present.
7. Normalize US phones to exactly 10 digits in source data and Excel only after source confirmation.
8. Assign vehicle/model exactly when supplied. A missing or `To be confirmed` model is a stop even when the name, address, and phone are complete; obtain an explicit M5S/M7S decision. If only color is missing and the user allows random color, select BK or RD and record the decision in `vehicle_assignment_note`.
9. Never copy old test users, old billing data, `View map`, an old customer's phone, or a map-search result into a new record.
10. Keep canceled historical orders as separate audit rows. Add a distinct pending row for a replacement order.

## Phase 2: Verify and stage

1. Check each shipping address against the approved evidence comparison before using Shopify's address recognition.
2. Use Google Maps only to validate an already exact, sourced address. Maps can never supply, normalize, replace, or resolve a conflicting component.
3. Keep apartment, suite, unit, floor, building, or front-desk instructions in `address2`.
4. Close the Maps tab after copying the confirmed address.
5. Mark each row `MATCH`, `REVIEW`, or `CANCELED`; never silently repair uncertain handwritten data.
6. Render or inspect the full batch and show the user the staged table before real submission.
7. Stop for human correction if any required field or address component remains uncertain.

## Phase 3: Submit one order at a time

### Resume and recovery behavior

Treat an open Shopify draft as the current checkpoint. When a run is interrupted or a locator fails,
inspect the current page and continue from the first missing field; do not restart from the beginning.
Before each action, scan whether the product, customer, shipping address, Notes, Tags, and payment
controls are already populated. Skip populated fields and never add a duplicate product/customer.

If Google Maps or a Google address suggestion/popup appears, capture the visible address in the log or
verification note, then close the popup/tab with its visible X/Close control and return to the Shopify
draft. Do not leave Maps or its popup covering the Shopify form.

If the browser offers to save a Google address, choose `No thanks` or close the popup. It is unrelated to
the order and must not replace source evidence or interrupt the draft.

If Shopify's displayed shipping address or Google Maps conflicts with the source address, stop automation.
Open the current source contract or creator message, manually transcribe every address component into the
staging row and Shopify's shipping-address editor, and compare the visible Shopify result again. Never
accept, copy, or normalize the conflicting Shopify/Maps value. If the source itself remains unclear, keep
the row `REVIEW` and do not submit.

If the flow appears stuck, report a field checklist (complete vs blank), inspect the current screenshot
and DOM, and repair only the first blank/inconsistent field. Search Shopify for the current email/order
before considering any retry after a possible submission.

### One-person one-shipment rule

For the current contract, one normalized creator email plus contract identity may have only one active
shipment/order. Before creating or retrying an order, search Shopify by email and name and inspect the
current draft/orders for an existing new `#VARLA` order. If one exists, stop duplicate creation and
reconcile that order instead. A later collaboration for another bike/model is a separate future
authorization and must use a new explicit collaboration row; it must not create a second shipment for
the current contract by accident or overwrite the first order.

Follow [references/adspower-runtime.md](references/adspower-runtime.md) to verify the local service,
resolve the configured profile, start or reuse it, and attach Playwright over CDP. Do not launch a
separate clean Chromium profile for Shopify.

Use the existing environment and command:

```powershell
Set-Location "C:\Users\<your-user>\Documents\电摩项目\shopify_order_bot"
& ".\.venv\Scripts\python.exe" main.py --step submit-test
```

Before the first real order, run:

```powershell
Set-Location "C:\Users\<your-user>\Documents\电摩项目"
& ".\shopify_order_bot\.venv\Scripts\python.exe" -m compileall -q ".\shopify_order_bot"
& ".\shopify_order_bot\.venv\Scripts\python.exe" -m pytest -q ".\shopify_order_bot\tests"
```

For every order:

1. Reuse the current authenticated AdsPower browser page. Do not refresh an open Shopify page.
2. Add `Aftersale-KOL/KOC Exclusive`, quantity 1.
3. Search the customer by email. If stored shipping data differs, edit or re-enter it from the current row.
4. Verify name, email, normalized phone, shipping address, product, Notes, and Tags.
5. Do not fill, copy, compare, or rely on billing address.
6. Add order tag `KOL-PETER`; use customer tag `KOL` when creating a new customer.
7. Leave marketing consent checkboxes off.
8. Choose `Collect payment` → `Mark as paid` → `Create order`.
9. Confirm the new order page shows `Paid` and `Unfulfilled`. Capture `#VARLA` when available.
10. If only `#D...` is visible after a confirmed paid/unfulfilled order, do not click Create order again. Write `#D` to `draft_order_code` with current status, URL, timestamp, and a `VARLA_PENDING_RECONCILIATION` marker; exclude that row from future submission selection.
11. Otherwise, immediately write the `#VARLA` code, current status, order URL, draft code, and timestamp to the same pending identity row before moving to the next person.
12. Report short progress in the form `N/total name #VARLA... or #D... (pending reconciliation) status`.

## Stop conditions

Stop immediately without refreshing, retrying, or advancing to the next row when:

- Shopify shows connection verification, CAPTCHA, risk verification, or reauthentication.
- The shipping address/phone differs from the approved evidence comparison, is missing, or was inferred.
- The final submit may have been clicked but the result is unknown. Search by email/name and inspect the live order before any retry.
- The page contains a test email or identity data from another customer.
- Excel has multiple ambiguous pending rows for the same identity.

## Shipment exception

If an order was created but later found to contain an unverified phone or wrong/conflicting address:

1. Do not create a replacement order or retry fulfillment.
2. Mark the local row `STOPPED - logistics correction required`, preserve the original `#VARLA` for audit, clear any invented phone, and record the creator-confirmed address.
3. Inspect the live fulfillment/tracking state first. If it is already dispatched or change capability is unclear, stop UI automation and hand it to logistics for interception/address correction.
4. Do not overwrite Feishu with a misleading “corrected” state until the live logistics outcome is verified.

If final submission might have occurred, first search Shopify by email/name/order code and inspect the
orders list. Do not submit again until duplicate creation has been ruled out.

Do not attempt to evade Shopify risk detection with fake human delays, browser fingerprint tricks, or
repeated retries.

## Phase 4: Reconcile and deliver

1. Read the Shopify orders list after the batch. Status may change from `Unfulfilled` to `Fulfilled`
   after warehouse/tracking automation.
2. Align results by normalized email plus identity. Never preserve result columns by physical row number.
3. Keep canceled old orders separate from new replacement orders.
4. Check that each expected person has the intended model, correct 10-digit phone, one new `#VARLA` or a single clearly labelled `#D` provisional result, correct status, and correct order URL.
5. Scan the workbook for formula errors and render both data and verification/result previews.
6. Run the project tests again before claiming completion.
7. Give the user the final mapping table and clickable links to `KOL_order.xlsx` and the project folder.

## Communication

For batches, give an estimated duration before starting. Keep updates brief and concrete. Do not claim
success from script exit alone; report only what was confirmed in Shopify and written to Excel.
