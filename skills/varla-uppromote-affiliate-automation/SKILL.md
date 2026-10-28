---
name: varla-uppromote-affiliate-automation
description: Create and manage Varla UpPromote affiliates from a supplied creator webpage or Feishu Base page. Locate each creator record and its name, email, code name, and code link; create or verify the KOL-$100 affiliate, coupon, custom path, and Electric Dirt Bike short link; write back and reread Feishu before drafting or explicitly sending the creator email. Use whenever a user gives one or more KOL/Feishu records and asks to create UpPromote codes, generate links, synchronize Feishu, or email affiliate information.
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


# Varla UpPromote Affiliate Automation

Create one creator's affiliate setup end-to-end without duplicating records or sending from the wrong mailbox.

## Fixed operating boundaries

- Use the existing authenticated AdsPower browser profile for Shopify and UpPromote only.
- Do **not** use AdsPower to send Gmail. Send email through the normal Google Gmail / Varla Gmail automation path, after verifying the sender is `info@varlascooter.com`.
- Use `飞书codex本地链接skill` for Feishu Base. Do not use `lark-cli`.
- Use `varla-gmail-automation` for email operations. Draft by default. A current-task instruction such as “发邮件”, “发送”, or “发这个链接给他们” is explicit send approval; do not ask for a second confirmation, but keep all sender, recipient, Sent-search, and script confirmation guards.
- Enforce this order for every creator: UpPromote affiliate → coupon → custom link → generated and saved short link → Feishu writeback and reread → Gmail. Never start the affiliate code/link email before Feishu reread succeeds.
- Never expose browser endpoints, API keys, cookies, tokens, or OAuth files.

## Entry input and record discovery

Treat the supplied KOL webpage or Feishu Base/table/record URL as the entry point. Do not require the user to manually provide a code, email, or name.

1. Locate the intended creator record from the supplied page. If it is a single-record or filtered page, use that record. If it is a table/view, use an optional user hint only to identify the visible creator; never assume the first row.
2. Read these fields from that record, then use `飞书codex本地链接skill` to reread the exact record through Feishu OpenAPI before any write.

| Field | Source / rule |
|---|---|
| KOL name | Feishu `KOL Name` field for record identity. If it is a handle, placeholder, or generic profile label, use a verified person name from the signed agreement or current order record only when it matches the exact same email; do not overwrite the Feishu name unless asked. |
| Email | Feishu `Email`; normalize by trimming and lowercasing for matching |
| Code | Feishu `code name`; retain its exact uppercase/lowercase spelling |
| Destination | `https://varlascooter.com/collections/electric-dirt-bike` |
| Feishu record | Use its record ID when available; otherwise match by normalized email, never visible row position |

`code name` is the source of truth. If it is blank, stop and report the missing value; never invent a code. An existing `code link` means UpPromote/link creation is already complete for that creator. Stop by default; when the user specifically asks to send or resume the email stage, verify the stored code/link by reread and resume with `--resume-existing-link` without recreating anything.

If a real person name has clear first and last components, split it between the UpPromote fields. If it is a handle or one-component identity, place the exact handle in `First name` and use `-` in the required `Last name` field; do not invent a surname. If UpPromote rejects a PascalCase handle as a single first name, split only its unambiguous capitalization boundaries (for example, `SampleCreator` → `Just` / `Creator`) and use that same normalized display name when locating the affiliate detail page and preparing the email.

## Workflow

## Fast execution and recovery rules

- Run `scripts/VarlaAffiliateAutomation/run_varla_affiliate.bat`; it selects the validated Python environment instead of Windows Store/system Python.
- Prefer `--record-id <rec...>` when the record ID is known. Otherwise use `--code-name <exact code>`; use name/email only when those are the available identifiers.
- Probe all AdsPower CDP markers concurrently with sub-second HTTP checks, then connect only to a responding browser. Never wait five seconds on every stale marker.
- Reuse the current authenticated Shopify page. Identify the real UpPromote iframe, inspect the current state, and repair only the first missing or inconsistent field.
- Wait for the exact next control or verified saved value; avoid fixed multi-second sleeps.
- After a click that triggers UpPromote loading or a save, allow a 5-7 second response window before deciding it failed. The UI can update late; do not immediately navigate away or restart the whole workflow while the action is still settling.
- After **Login as affiliate**, select the newly opened dashboard whose body contains the exact creator name or code, so an older dashboard tab cannot receive clicks.
- Match `Electric Dirt Bike` exactly; do not select `Electric Dirt Bike Accessories`.
- Emit progress for AdsPower, affiliate, coupon, custom link, short link, Feishu, and Gmail stages immediately so a wait is visible and diagnosable.
- Search Gmail with scoped server-side `in:drafts` and `in:sent` queries and fetch only matching candidates. Preserve the existing idempotency checks.
- Treat order/shipping emails and affiliate code/link emails as different message types. An earlier order email does not prove the affiliate email was sent.
- If the user changes sequence, says “先不发”, cancels, or resumes while Gmail work may already have started, stop the mutation and reconcile with a narrow `in:sent` search using the exact recipient plus code, short-link slug, or order number. Never retry until Sent is checked.
- Before navigating, inspect open pages for the exact target email/code and classify the current stage as create form, coupon form, affiliate detail, affiliate dashboard, or open product-link modal. Resume that stage in place; do not restart from the Affiliate list.
- At the start of every new code-name task, navigate to and refresh the initial Affiliate list URL so the previous creator's detail page can never be mistaken for the new task. Resume in place only when the open page already contains the exact current creator email/code. Within the same task, a matching Coupon page may still open the creator detail inline.
- In the affiliate table, anchor actions to the `tbody tr` containing the exact email. Search chips above the table are not affiliate rows.
- Do not depend on the displayed affiliate name to open a detail page: after anchoring the exact-email row, use that row's name/action element. This is required when UpPromote normalizes a handle's capitalization or spacing.
- Click the outer `.ant-select-selector` for Selected collections; the placeholder text is covered by that element and is not itself the click target.
- Whenever **Manage coupons** opens during the normal creation path, click **Add coupon** immediately. Do not open **View assigned coupons** before the first save. Recovery exception: if Save was clicked but the result is ambiguous, inspect **View assigned coupons** once before retrying; if the exact code is already assigned, continue instead of creating a duplicate.
- On a resumed or interrupted creator run, inspect **View assigned coupons** before entering a new code. Continue only if the exact code is visibly assigned and the `$100` amount is verified; otherwise return to **Add coupon**. Never create a second coupon solely because the prior worker stopped after a save.
- After a successful save, UpPromote resets the **Add coupon** form to blank values (`0.00`, unchecked combinations, and no code). This reset is expected and does not mean the coupon disappeared. Treat `Coupon assigned` as the save signal, then use **View assigned coupons** for readback; verify exactly one row for the code, `$100`, and all three combination icons before any retry.
- Under **Combinations**, force-check and then verify all three options before saving: `Product discounts`, `Order discounts`, and `Free shipping discounts`. Text-label lookup must fall back to the checkbox in the same row because UpPromote labels are not always bound to their inputs.
- Treat the detail page as ready only after the exact creator email is present; `N/A` and blank general information are loading skeletons.
- UpPromote buttons are not consistently exposed through accessibility roles. Prefer exact button text, then use a scoped CSS button fallback inside the active modal.
- Shopify's outer chrome can be localized while UpPromote remains English. Treat both `Save`/`保存`, `Discard`/`放弃`, and `Unsaved changes`/`未保存的更改` as equivalent global controls/statuses before judging a save as failed.
- When an approved send finds a matching existing Gmail draft, resolve its draft resource ID and send that exact draft. Never create a second message.
- Query `users.drafts.list` with the same narrow recipient/subject filter and carry its returned draft resource ID directly into `drafts.send`; do not scan every mailbox draft.
- Flush the structured browser result and exit the worker process immediately while leaving the AdsPower browser open, so Feishu and Gmail stages cannot hang behind a live CDP socket.
- After each creator succeeds, close that creator's affiliate-dashboard tab. On failure, close the failed creator page and reopen the Affiliate list so the next creator cannot inherit an unsaved form or stale dialog.

## One-click script

The installed skill directory contains a live directory link at
`scripts/VarlaAffiliateAutomation` pointing to the validated output package.
Use its `run_varla_affiliate.bat`, or invoke the installed launcher:

```powershell
python scripts/run_varla_affiliate.py --feishu-url "<Base URL>" --kol-name "<exact KOL name>"
```

The script defaults to a Gmail draft. A live send additionally requires
`--send --confirm SEND`. Use `--dry-run` for read-only Feishu/template validation,
and `--resume-existing-link` only to resume the email stage after a verified
Feishu link already exists. The script performs duplicate checks before every
UpPromote creation and Gmail mutation.

### 1. Feishu gate

1. From the supplied webpage, identify the selected creator record and reread it through Feishu OpenAPI by record ID or normalized email.
2. If `code link` is already populated, stop UpPromote creation and report the existing code/link. Create no duplicate. Resume only the email stage when the current request explicitly asks for it and the stored value passes reread verification.
3. Confirm `code name` is populated. If missing, stop and report it as missing.

### 2. UpPromote duplicate gate

1. Reuse the user-designated AdsPower profile and its current Shopify session.
2. Open UpPromote → **Affiliates** and search by the exact creator email.
3. If an affiliate exists, inspect its program, coupon, and code before continuing. Never create a second affiliate for the same email.
4. If there is no record, add one with:
   - Notification email: `Yes`
   - Program: `KOL - $100`
   - Status: `Active`
   - Password type: `Auto generated password`
   - Correct first/last name and creator email
5. Save once and confirm the success notice. Re-search the exact email to verify exactly one result.

### 3. Coupon setup

From that affiliate row, open **Manage** under Coupons and immediately click **Add coupon**. Do not open **View assigned coupons** during the normal first attempt.

- Create a coupon using these exact rules:
  - Coupon code: the Feishu `code name`
  - Discount type: `Product discount`
  - Value type: `Fixed amount`
  - Amount: `$100`
  - Applies to: `Specific collections` → `Electric Dirt Bike`
  - Combinations: enable product, order, and free-shipping discounts
  - Minimum requirement: none
  - Usage limit: none
- Save and require an UpPromote confirmation such as `Coupon assigned`.
- If the save result is ambiguous, use **View assigned coupons** only as a recovery check. When the exact code is present there, treat the coupon as assigned and do not recreate it.

### 4. Custom affiliate link and short product link

1. Open the affiliate detail page and enter the exact coupon code as its custom affiliate-link path; save and verify it remains set.
2. Select **Login as affiliate**. In the affiliate dashboard, click **Get product link**.
3. Choose `Enter a link`, paste the fixed Electric Dirt Bike destination, then click **Generate**.
4. Click **Get shortened link**. Require a non-empty returned short URL (normally `https://bit.ly/...`).
5. Click **Copy & save** and verify the short URL appears in the Saved link table.
6. Always perform this generation sequence for the current task; do not reuse a URL merely because an older entry is already visible in the Saved link table. Write back only the URL returned and saved by the current generation.
7. Close the completed creator's affiliate-dashboard tab before moving to the next creator.

### 5. Feishu writeback

Update only the matched record's `code name` and `code link`, then immediately read it back.

`code link` is a Feishu URL field; write it as:

```json
{"link":"https://bit.ly/example","text":"https://bit.ly/example"}
```

Report success only when the reread record has the exact code and short link.

### 6. Creator email

Create this email in standard Gmail, not AdsPower Gmail:

- Enter this stage only after the exact `code name` and `code link` were reread successfully from Feishu for this creator.
- Sender must be verified as `info@varlascooter.com` before a mutation.
- Recipient: the exact Feishu creator email.
- Prefer replying in the creator's existing verified thread when one exists, preserving its subject and thread. Otherwise create a new message with the standard subject.
- Source the wording from bundled `scripts/VarlaAffiliateAutomation/assets/Varla KOL Code.docx` (or an explicit `--docx` override): use its first non-empty paragraph as the subject and the remaining paragraphs as the body.
- Current subject: `Varla Affiliate Code & Tracking Link`
- Replace `[Creator Name]`, `[CODE]`, and `[LINK]` with the matched creator information. Remove decorative emoji from the greeting name.
- The DOCX is a wording source only. Do not attach it to the email.
- The DOCX template is the default for full affiliate onboarding. When the user directly says to send “this code/link”, a concise thread reply containing the verified code and short link is acceptable; never attach the DOCX.
- Draft by default. When the current request explicitly says to send, treat that instruction as approval and proceed without asking again; the script still requires `--send --confirm SEND`.
- Before every send, search Sent narrowly for the exact recipient plus code and short-link slug. The idempotency key is recipient + code + short link. If found, report `already sent` and skip the mutation.
- After sending, reread the Sent message and verify sender, recipient, thread/subject, code, and short link. A success response without this readback is not completion.
- Use real paragraph breaks, never visible `\\n` or `\\r\\n` strings.

Template:

```text
Hi {{creator_name}},

Thank you so much for your support and for partnering with Varla! 🙌

Your personal affiliate information is below:

Discount Code:
{{code}}

Affiliate Link:
{{short_link}}

Your audience can use this code to receive a discount, and any successful orders through your link/code will be tracked automatically.

You can check your sales performance, orders, and commission results through the affiliate tracking system.

When we created your account on the affiliate platform, an automated system email was sent to you with your UpPromote platform access link, account information, and login details.

Please check your inbox for that email. If you don’t see it, please also check your spam/junk folder or promotions folder, as it may have been filtered there.

If you still cannot find it, please let us know and we’ll help you check it.

We truly appreciate your support and the effort you put into creating content for Varla. We’re excited to see the impact we can create together and look forward to building a long-term partnership with you!

Thank you again! ❤️

Best regards,
Team Member
Varla Team
```

## Recovery and stop conditions

- A Shopify/UpPromote save with an unknown result: search by email and coupon before retrying.
- CAPTCHA, reauthentication, risk verification, ambiguous duplicate, coupon conflict, or a missing code: stop without guessing or retrying writes.
- Gmail sender is not `info@varlascooter.com`: do not send. Preserve the draft and report the mismatch.
- A Gmail send result is ambiguous: do not resend automatically; search Sent and report the result.
- A cancellation or reordered instruction arrives during Gmail delivery: reconcile Sent first, then follow the newest instruction. Never assume the previous mutation did or did not happen.

## Completion report

Use this compact format:

```text
Creator: <name> <email>
Source record: <Feishu record ID or matching normalized email>
Affiliate: created / existing verified
Code: <code>
Short link: <link>
Feishu: reread verified
Email: draft created / sent from info@varlascooter.com
Email verification: Sent reread verified / already sent and skipped / not requested
```
