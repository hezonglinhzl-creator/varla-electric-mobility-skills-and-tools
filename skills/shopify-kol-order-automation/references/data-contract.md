# Shopify KOL Workbook Data Contract

Use worksheet `KOL Order` in:

`C:\Users\<your-user>\Documents\电摩项目\shopify_order_bot\KOL_order.xlsx`

## Input and staging columns

| Column | Field | Rule |
|---|---|---|
| A | `name` | Full recipient name |
| B | `email` | Primary identity key for Shopify lookup |
| C | `phone` | US number stored as exactly 10 digits |
| D | `address` | Street number and street only |
| E | `city` | City |
| F | `state` | Full state name |
| G | `country` | `United States` for US orders |
| H | `zipcode` | ZIP as text so leading zeroes survive |
| I | `product` | `Aftersale-KOL/KOC Exclusive` |
| J | `note` | Vehicle code, newline, `VAR-GIFTSET-002` |
| K | `tag` | `KOL-PETER` |
| L | `address2` | Apartment/suite/unit/floor/building/front desk only |

## Result columns

| Column | Field | Rule |
|---|---|---|
| M | `varla_order_code` | New `#VARLA` from the created order; do not put a `#D` value here |
| N | `shopify_order_status` | Current observed status |
| O | `shopify_order_url` | Direct Shopify Admin order URL |
| P | `draft_order_code` | `#D...` when captured; if a paid/unfulfilled order exposes only this identifier, it is a provisional completed result |
| Q | `shopify_created_at` | Local creation timestamp |
| R | `feishu_sync_status` | Leave blank unless the user explicitly requests Feishu writeback; then use `飞书codex本地链接skill` and record the verified sync result |
| S | `vehicle_assignment_note` | Explain inferred model/color |
| T | `address_verification_status` | `MATCH`, `REVIEW`, or `CANCELED` |
| U | `address_verification_note` | Visible confirmed Maps address or review reason |
| V | `source_file` | Contract/image/document filename |
| W | `kol_code_name` | Contract `Code Name`, preserved exactly without surrounding label |
| X | `impact_id` | Contract `Impact ID Number`, stored as text |
| Y | `shipping_phone_source` | Required before submission: exactly `CONTRACT` or `CREATOR_MESSAGE`; `MISSING`, inferred, or copied phones stop the order |
| Z | `shipping_address_source` | Required before submission: `CONTRACT_EXACT`, `CREATOR_MESSAGE`, or `CONTRACT_AND_CREATOR`; a map-inferred address alone stops the order |

### Provisional Shopify result

Some Shopify order pages may finish creation while exposing only `#D...` rather than `#VARLA...`.
When the live page also confirms `Paid` and `Unfulfilled`, write the status, direct URL, timestamp, and
`#D` value to `draft_order_code`; keep `varla_order_code` empty and set the local reconciliation marker
to `VARLA_PENDING_RECONCILIATION`. This row is created, not pending: exclude it from later submission
selection and reconcile the canonical `#VARLA` code by normalized name/email when Shopify exposes it.

## Optional Feishu writeback

Only after an order is confirmed in Shopify and the user asks for Feishu sync:

1. Use `飞书codex本地链接skill`, not `lark-cli`.
2. Resolve the current Base/table URL from the user input and read fields and records first.
3. Match the existing record by normalized email before handle or name.
4. Write the confirmed `#VARLA` order code, `kol_code_name`, and `impact_id`; attach the matching contract if requested.
5. Re-read the changed record and set `feishu_sync_status` only after the values are verified.

For a contract attachment larger than 20 MB, use Feishu's `upload_prepare` → 4 MB `upload_part` blocks
→ `upload_finish` flow. Preserve existing attachments and read back the attachment filename before
marking the local row synchronized.

## Phone normalization

For United States rows:

1. Remove spaces, parentheses, hyphens, and other non-digits.
2. If there are 11 digits starting with `1`, remove the leading `1`.
3. Require exactly 10 remaining digits.
4. Save the 10 digits in Excel and input data.

## Source-confirmation gate

- A syntactically valid phone number is not enough: it must appear in the current contract or in a direct creator message.
- Google Maps may confirm a supplied address, but must never invent, replace, or fill an uncertain street/city/ZIP.
- A literal `To be confirmed` is not a source value. Use a later complete value on the same source line only when it is unambiguous; otherwise stop the row.
- If the contract omits the phone, or the contract and creator message disagree on the address, set the source field to `MISSING`/`REVIEW` and stop before Shopify. Do not substitute historical customer data or a guessed value.

Shopify may display `+1` after saving. Compare the normalized final 10 digits; do not copy `+1` back
into Excel.

## Vehicle note codes

| Vehicle | Color | First Notes line |
|---|---|---|
| M5S | Black/BK | `V-M5S-BK-US` |
| M5S | Red/RD | `V-M5S-RD-US` |
| M7S | Black/BK | `V-M7S-BK-US` |
| M7S | Red/RD | `V-M7S-RD-US` |

Second Notes line is always `VAR-GIFTSET-002`.

If the model is missing or `To be confirmed`, stop before staging or submission. An explicit user decision
may supply the model; only a missing color may be randomized when the user has allowed it.

## Identity and duplicate rules

- Match a live result to the pending row by normalized email and name, not row number.
- When the same email has a canceled historical row and one blank pending row, write the new order only
  to the blank pending row.
- Never overwrite the canceled row with the replacement result.
- If more than one blank pending row remains for the same identity, stop for manual resolution.
- Test emails such as `@example.com`, `.test@`, or `+test@` cannot be submitted as real orders.

## Address rules

- `address` contains only the primary street line.
- `address2` contains delivery details such as `Apt 4`, `Floor 4`, or `Front Desk`.
- `View map` is Shopify UI decoration and is never part of address data.
- Billing address is not an input source and cannot satisfy shipping validation.

## Contract outreach identifiers

- Capture `Code Name` and `Impact ID Number` when they appear in the shipping/signature section.
- Do not confuse `Code Name` with the Shopify Notes vehicle code.
- Keep Code Name's original spelling/case unless the user asks to normalize it.
- Store Impact ID as text so leading zeroes cannot be lost.
- These fields are shipment/reference metadata only; do not type them into Shopify Notes or Tags unless
  the user explicitly changes the order format.
