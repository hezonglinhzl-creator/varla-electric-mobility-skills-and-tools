---
name: varla-kol-contract-updater
description: Update Varla KOL collaboration agreements (.docx or .pdf) with creator identity, email, shipping details, commission rate, date, bike model, code name, and other supplied terms while preserving layout and removing previous creator data. Also audit contract video-deliverable counts. Use whenever the user asks to update a Varla KOL contract, customize a creator agreement, change a bike model, prepare a signed-contract attachment, normalize contract filenames, or count videos required by KOL contracts.
---

# Varla KOL Contract Updater

## Fixed shipping-contract template

For future shipping-contract creation, use this source template unless the user explicitly supplies a different template:

`C:\Users\<your-user>\Downloads\合作合同\2026-08-06_Varla_KOL_Agreement_M7S_creator@example.com.docx`

Create a separate dated creator-specific output copy from this source. Shared `Content Creation Requirements` and the matching M5S/M7S Brief are uploaded directly from their original source files and are not copied per creator.

**Canonical path (supersedes any mojibake path above):** `C:\Users\<your-user>\Downloads\合作合同\2026-08-06_Varla_KOL_Agreement_M7S_creator@example.com.docx`

Treat the canonical template as read-only. Never modify, rename, move, or delete it; generate a separate creator-specific contract copy before shipping extraction.

## Workflow

1. Read the source DOCX completely, including paragraphs, tables, headers, footers, and OOXML text.
2. Extract the previous creator's name, email, handle, address, phone, discount code, rate, date, and bike/product model.
3. Use only facts supplied by the user or clearly visible in an attached image.
4. Do not infer a social handle, address, phone, discount code, or bike model. Set missing fields to `To be confirmed`.
4a. Every creator receives an individually customized agreement. Never reuse another creator's identity, shipping details, commission, code, signature, or old model.
5. Save changes back to the source agreement by default. Create a separate agreement only when the user explicitly requests a copy. In either case, use `YYYY-MM-DD_Varla_KOL_Agreement_<model>_<creator-email>.<ext>` for renamed creator-facing files. The filename must always contain the confirmed model (for example, `M5S` or `M7S`); do not use `TEST`, `TEST_ONLY`, or test-run IDs.
6. Run `scripts/update_contract.py` for deterministic field replacement.
7. Verify:
   - the new name, email, rate, date, and bike model are present;
   - previous creator-specific strings and the old contract model are absent from the replaced model fields;
- table count and table shapes are unchanged; the legacy `Impact ID Number` paragraph is intentionally removed when present;
   - the document renders cleanly to page images when a renderer is available.
8. Return the final agreement path and mention any fields left as `To be confirmed`.

## Video Deliverable Audit and Feishu Writeback

Use this mode when the user asks to count or locate KOL video obligations. Audit is read-only by default. Write back to Feishu only when the user explicitly asks to fill or update a named field, such as `签订数量`.

1. For a Feishu Base request, use `飞书codex本地链接skill` and `lark-cli base` to resolve the exact table, list its fields, and list the target records. Download the exact `合同` attachment for every target record with `record-download-attachment`; do not infer a contract from a similarly named local file. A previously downloaded local copy may be reused only when its attachment filename and size match the current Base attachment.
2. Read every contract and match it back to its Base record by attachment plus KOL name/email. Count only the explicit deliverable clause, not incidental references to video length, platforms, previews, raw footage, or usage rights.
3. Treat `Both videos` as 2, `1/2/3/4/12 videos` as the stated count, and an explicit long-form YouTube-video requirement as 1. Sum distinct commitments in one clause: `2 short-form videos plus 1 YouTube video` = 3.
4. Preserve ranges exactly during reporting: `2–3 per week for 8 weeks` = 16–24; `one YouTube review plus 4–6 Reels` = 5–7. Never reduce a range to a guessed integer. For a writeback, leave range values blank unless the user explicitly authorizes text ranges in the destination field.
5. If the clause says `discussed`, is blank, or remains unreadable after rendering a scanned PDF, mark it `数量未写` in the report and do not write a guessed value.
6. For an authorized `签订数量` writeback, update only records that have a contract, a clearly fixed numeric count, and an empty target cell. Never overwrite an existing value. Do not create rows for records without contracts.
7. Batch update only the named field, then re-read every changed record and confirm the field value exactly. Report: target records, contracts found, rows filled, rows kept, no-contract rows ignored, ranges left blank, and `数量未写` rows.
8. Report the distribution (for example, how many creators owe 2, 3, or 4 videos) and a KOL-name/email list for every nonstandard, range, or unconfirmed count. Status such as `已发布` is not proof that the contracted number has been delivered.

## Command Center Handoff

- Generate an agreement only after the creator identity, recipient email, commission, date, and bike model have been reviewed. Keep unsupported values as `To be confirmed`.
- Edit and save the original agreement in place by default. Create a separate copy only when the user explicitly asks to retain the source or requests an output copy.
- Keep the agreement, content-creation requirements, and corresponding M5S/M7S brief as three separate attachments for every contract email. Generate and name only the agreement as a dated creator-specific file. Upload the two shared source documents directly, without copying, renaming, editing, moving, or deleting them unless the user explicitly asks.
- Before handing files to Gmail, return the final absolute paths and verification summary. Gmail remains responsible for thread continuity, draft/send guards, and attachment hashing.
- When the files belong to an existing creator conversation, Gmail must attach them in a reply to that exact thread. The authenticated sender is `info@varlascooter.com`; the recipient is the latest verified external sender. Preserve the original `threadId`, `In-Reply-To`, `References`, and subject instead of opening a new compose message.
- If the source thread, latest external recipient, or thread headers cannot be verified, stop the handoff and keep the files local. Do not create a standalone message as a fallback.
- In tests, `hzl` means `test@example.com`. A test recipient does not remove the normal draft-first and explicit-send requirements.
- Command-center health checks may use a synthetic legacy agreement containing `Impact ID Number`. Removing only that deprecated paragraph is an expected migration and must not be reported as structural damage; any other paragraph/table/section shape change still fails closed.

## Current Project Rules

- A creator may complete and sign the DOCX directly. Do not ask for a second signature or insist on PDF conversion unless the user explicitly requires PDF.
- When the user asks to change only the product model, use `--model-only`: change only the body model sentence, `Bike / Product Model` table row, and model-specific hashtag. Do not alter confirmed creator identity, commission, date, or logistics fields.
- When no new model is supplied, write `To be confirmed` in the body and table and remove old model-specific hashtags. Never preserve the old model by default.
- In a newly prepared unsigned agreement, keep `Signature of the Influencer:` blank unless the creator's signature text is explicitly supplied. In `--model-only` mode, preserve an existing signature because the agreement may already be signed.
- Never include an `Impact ID Number` field. Remove that entire legacy paragraph when it exists in the source.
- `Impact ID Number` is permanently excluded from every creator-specific agreement, including unknown-value cases; never write `Impact ID Number: To be confirmed`.
- Keep `Exclusive $100 Discount Code for Your Audience` as a statement only. Clear any historical code value printed after it; the $100 coupon is for the creator's audience, not a payment to the creator.
- Write commission in English only, for example `Commission Rate: 4% (Valid for 2 months)`; never append Chinese commission wording.
- When renaming an existing agreement, use the date and model visible in the agreement or explicitly supplied by the user. Use `YYYY-MM-DD_Varla_KOL_Agreement_<M5S-or-M7S>_<email>.<ext>` and preserve the original extension.
- Before an email attachment is prepared, check the final agreement filename, the creator name/email, model/hashtag, and signature state. Also copy and attach `C:\Users\<your-user>\Downloads\合作合同\Varla KOL Content Creation Requirements.docx` plus the model-specific source brief: `VARLA M5S Brief(1).docx` for M5S or `VARLA M7S Brief(1).docx` for M7S. These two documents remain separate and are not edited unless requested.

## Command

Use the bundled Python runtime when available and quote Windows paths:

```powershell
& "C:\Users\<your-user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/update_contract.py `
  --input "source.docx" `
  --output "updated.docx" `
  --name "Creator Name" `
  --email "creator@example.com" `
  --rate "5%" `
  --date "July 29, 2026" `
  --bike-model "Varla M7S"
```

Optional inputs are `--bike-model`, `--color`, `--accessory-note`, `--handle`, `--shipping-address`, `--phone`, `--discount-code`, and `--signature-name`. Use `--color "Black"` to display `Varla M5S (Black)` in the agreement while keeping the matching model hashtag as `#VarlaM5S`. Use `--accessory-note "A helmet will be provided separately and may arrive after the bike."` only for an explicitly approved accessory commitment. If `--bike-model` is omitted, write `To be confirmed` instead of retaining the old model.

For a model-only update:

```powershell
python scripts/update_contract.py `
  --input "source.docx" `
  --output "2026-07-30_Varla_KOL_Agreement_M7S_creator@example.com.docx" `
  --model-only `
  --bike-model "Varla M7S"
```

## Editing rules

- Keep the original layout, styles, images, product terms, deliverables, advertiser contact, and legal wording unchanged.
- Change only creator identity/contact fields, rate, date, bike model, model hashtag, and explicitly supplied creator-specific values.
- Update the bike/product model in both the acknowledgement text and the `Bike / Product Model` table row. Replace model-specific hashtags with the new model hashtag.
- Use the creator's full name where the old contract used an unverified social handle unless the user supplies a new handle.
- Keep `Signature of the Influencer:` blank for the creator to sign personally. Fill it only when the user explicitly supplies `--signature-name`. Preserve it in `--model-only` mode.
- Never leave the previous creator's shipping, phone, or discount code in the output. The Impact ID line must be removed entirely.
- Save to the original source by default. Create a separate output copy only when explicitly requested.
