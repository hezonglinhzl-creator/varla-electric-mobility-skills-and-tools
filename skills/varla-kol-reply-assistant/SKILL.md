---
name: varla-kol-reply-assistant
description: Maintain, migrate, package, and update Team Member's Varla KOL reply assistant and its command-center integration across Windows projects. Use when the user mentions KOL reply software, Varla/Himiway reply templates, Chrome extension replies, local WebUI previews, Gmail classification, OCR paste/screenshot recognition, Instagram/TikTok/Gmail reply generation, knowledge_seed, split_playbooks, or asks to update/repackage the assistant.
version: "2026.08.07.1"
---

# Varla KOL Reply Assistant

Use this skill to maintain the local Varla KOL reply assistant and its knowledge base.
The assistant is a local Windows tool plus Chrome MV3 extension for drafting replies. It must never auto-send messages.

## Core Rules

1. Preserve user files. Do not batch-delete files or folders.
2. Identify the active runtime before editing. In the standalone assistant, `chrome-extension/contentScript.js` is the main product; in `varla-kol-command-center`, the local WebUI and API are the primary controller.
3. Keep OCR local through bundled Tesseract assets when available. Do not upload screenshots to external services by default.
4. Generate reply choices for manual copy/insert only. Never click send, never auto-submit.
5. Keep uncertain product specs, commercial terms, and campaign terms explicit. Do not invent details.
6. Use short natural DM style for Instagram, TikTok, Meta Business Suite, and structured professional style for Gmail.
7. Default reply count should stay compact. If the current UI says 3 replies, preserve that unless the user asks otherwise.
8. Current shipping rule: collaboration orders usually ship within 1-3 days after collaboration confirmation; regular purchases usually ship within 1-3 days after purchase; tracking is shared once available. Do not use old July/pre-order/launch timing.
9. Generate and show a preview before any Gmail action. Medium/high-risk content may be shown for review, but sending stays locked until the applicable human confirmation and safety checks pass.
10. Keep knowledge updates low-frequency. Sync Feishu every 2-3 days unless the user explicitly requests an immediate sync.
11. For Gmail replies, keep roles fixed: `info@varlascooter.com` is the authenticated outbound sender; the latest verified external sender is the reply recipient. Never reverse them.
12. Existing Gmail conversations must remain in the original thread with the original subject, `threadId`, `In-Reply-To`, and `References`. Never use a new compose action for a reply, correction, attachment, or status update.
13. An ignore action applies only to the exact clicked local task ID. It must not ignore another task from the same sender, thread, category, or filter result.
14. Contract-stage previews must use the local knowledge base for the model, commission, coupon, content scope, and collaboration stage before drafting.
15. Contract-stage email previews must list three separate attachments: the creator-specific agreement, the original shared `Varla KOL Content Creation Requirements.docx`, and the original matching M5S/M7S Brief. The two shared source files are uploaded directly and are never copied, renamed, edited, moved, or deleted by the assistant.
16. Render email bodies with real UTF-8 paragraph breaks between sentences. Never expose literal `\\n`, `\\r\\n`, escaped JSON, or other formatting artifacts in a reply preview.
14. A failed or uncertain Gmail action must remain visibly unsent and recoverable for review. Never show success or remove the task unless Gmail returns and verifies the resulting message/thread state.
15. The reply UI must support Chinese keyword search across stage names, keywords, and template text. Search may narrow the visible stage list, but must not change knowledge files.
16. OCR input must accept pasted screenshots, dragged image files, and selected image files. If clipboard image metadata is unavailable, fall back to file picker or drag/drop instead of throwing a `getURL`-style error.
17. Keep the default response set compact: one useful reply per tone is sufficient unless the user explicitly requests more alternatives.

## Project Discovery

When the user gives only a folder or says "update the reply program", inspect before changing.

Common project root:

`E:\himiway\KOL回复训练\脚本\varla-kol-reply-assistant`

Expected important files:

- `chrome-extension/contentScript.js`: main floating in-page widget, stage rules, local OCR, reply generation, manual insert.
- `chrome-extension/manifest.json`: Chrome MV3 manifest.
- `chrome-extension/vendor/`: bundled Tesseract OCR runtime and language data.
- `src/app.js`: fallback local web UI and ChatGPT prompt builder.
- `src/stageRules.js`: fallback UI stage classification.
- `knowledge_seed/templates.json`: legacy/full template bank.
- `knowledge_seed/product_specs.json`: confirmed product specs.
- `knowledge_seed/Varla_KOL_常见问题回复库.md`: internal common reply bank.
- `knowledge_seed/split_playbooks/knowledge_index.json`: lightweight routing index.
- `knowledge_seed/split_playbooks/kol_templates.json`: KOL collaboration templates.
- `knowledge_seed/split_playbooks/presales_aftersales_templates.json`: purchase, shipping, support, repair, refund templates.
- `knowledge_seed/split_playbooks/dealer_service_partner_templates.json`: dealer, service partner, wholesale, bulk, unknown-intent templates.

If paths differ in another project, locate files by name with fast search rather than assuming this exact path.

Command-center root:

`C:\Users\<your-user>\Documents\电摩项目\varla-kol-command-center`

Important command-center files:

- `app/production_services.py`: deterministic classification, reply-stage selection, preview persistence, and Gmail adapters.
- `app/reply_engine.py`: approved knowledge retrieval, template rendering, and risk-gated preview generation.
- `app/catalog.py`: hash-approved `templates.json` and `product_specs.json`.
- `app/web/app.js`: clickable task filters, preview editor, and manual confirmation controls.
- `app/skill_health.py`: Gmail, Feishu, reply assistant, database, and contract-tool health.

## Knowledge Loading Pattern

Keep the split knowledge design. Do not restore startup loading of all template data.

Preferred flow:

1. Read `knowledge_seed/split_playbooks/knowledge_index.json`.
2. Route the incoming message to one category:
   - Pure KOL/collaboration/content/contract: `kol_templates.json`.
   - Presales/aftersales/price/stock/shipping/repair/refund: `presales_aftersales_templates.json`.
   - Dealer/service partner/wholesale/bulk/unclear business intent: `dealer_service_partner_templates.json`.
3. Load `product_specs.json` only when exact M5S/M7S facts are needed.
4. Use Markdown playbooks for human/agent reference, not as startup-heavy runtime payload unless the user asks.

## Reply Policy

Use these business rules when editing templates or prompts:

- Pre-sales email: `support@varlascooter.com`.
- After-sales email: `customer@varlascooter.com`.
- Low-risk price, discount, promo, stock, and availability questions can route to the Instagram Bio link for latest information.
- Complex order, address, shipping cost/timing, payment, or manual review questions route to pre-sales.
- Repair, warranty, product issue, ZIP-code repair-location, refund, or customer service questions route to after-sales.
- Broken e-bike: ask for clear multi-angle photos/videos and ask the customer to email the same evidence to after-sales.
- Front brake line: say it should be routed inside the panel; share the repair/install YouTube link if needed.
- Assembly, installation, repair-video, or tutorial questions: say Varla has assembly and repair/tutorial videos on the YouTube channel and the user can check the relevant video there first.
- Actual after-sales, repair, warranty, refund, brake, battery, or product issues must route directly to `customer@varlascooter.com`; say the after-sales team can review the case more professionally and provide the most accurate support.
- When a KOL has received or assembled the bike, encourage the first showcase and ask them to send the first draft, first ride clip, or post link when ready.
- Product appearance before filming: check stickers, wiring/line bundling, and visible product condition.
- Official tags: Instagram `@varla_adventure`, TikTok `@varla_sport`, YouTube Shorts and long-form descriptions `@Varla_sport`.
- YouTube rules apply to both Shorts and long-form videos.
- Closed beta question: use the approved wording `The current closed beta event offers a discount of nearly 50 per cent; you can join the community mentioned in my bio to find out more.` Do not invent a date, price, or extra discount condition.
- Do not mention commission unless there is a direct commercial/affiliate question or Team Member provides approved wording.
- If commission is directly asked and approved context is needed, use 4%-8% range with 5% as standard; 6%-8% needs strong evidence and explicit approval.

## Command Center Workflow

1. Search and read Gmail messages from the latest 30 days that concern collaboration, sponsorship, affiliate/commission, creator identity, contracts, content requirements, shipping, orders, pre-sales, or after-sales.
2. Route into `kol`, `pre-sales`, `order-logistics`, or `after-sales`. Add the existing exact `KOL` label only to confirmed collaboration threads.
3. Select an approved reply stage deterministically. Never ask a model to invent the stage or commercial facts.
4. On **生成并预览**, retrieve the relevant local knowledge, generate one editable preview, display it beside the task, focus the editor, and keep the task in human-control mode.
5. Mixed-category, personal-data, commission, contract, refund, legal, or unsupported-fact cases remain `manual_review`. A useful preview may still be displayed, but confirm-reply and confirm-forward remain locked when policy requires it.
6. Immediately before reply/forward confirmation, re-read the full Gmail thread and re-run knowledge, stale-message, recipient, and risk checks.
7. Never auto-send. Forward pre-sales/order questions only to `support@varlascooter.com`; forward after-sales questions only to `customer@varlascooter.com`.
8. In the final confirmation, show the fixed sender `info@varlascooter.com` separately from the action target. For a reply, the target is the canonical latest external sender and the operation must preserve the source Gmail thread; for a forward, the target is the approved internal routing mailbox.
9. Treat quoted `"info@varlascooter.com" <info@varlascooter.com>` as the local account only when both values canonicalize to the same address. Any different address-like display name is ambiguous and stops the Gmail action.
10. **忽略** changes only the clicked task ID to ignored. **确认回复/确认转发** changes only that task after Gmail verification succeeds; on failure, leave it visible with the exact error and no sent state.
11. Health must distinguish reply-project syntax/catalog drift from Gmail authorization. A reply-assistant version change may require reviewed lock acceptance, but it must never force a Google login.
12. The active Windows source is `E:\himiway\KOL回复训练\脚本\varla-kol-reply-assistant`; verify that exact directory before validating hashes or editing runtime files.

## Shipping Rule

Remove old wording from code, docs, templates, and Word playbooks:

- Do not say July.
- Do not say 7月.
- Do not say pre-order / preorder when referring to timing.
- Do not say launch timing / listed in July / available around July.
- Do not promise a specific delivery date.

Use this instead:

```text
For collaboration orders, shipping is usually arranged within 1-3 days after the collaboration is confirmed.
For regular purchases, shipping is usually arranged within 1-3 days after purchase.
We will share tracking information once it is available.
```

Chinese internal note:

```text
合作确认后通常 1-3 天安排发货；普通购买后通常 1-3 天安排发货；tracking 出来后同步；不承诺具体到货日期。
```

## Update Workflow

1. Inspect current project files and identify active copy.
2. Search for relevant existing text with `rg`.
3. Update both fallback UI and Chrome extension when reply behavior changes:
   - `src/app.js`
   - `src/stageRules.js`
   - `chrome-extension/contentScript.js`
4. Update knowledge files when business rules change:
   - `knowledge_seed/templates.json`
   - `knowledge_seed/Varla_KOL_常见问题回复库.md`
   - `knowledge_seed/split_playbooks/*.md`
   - `knowledge_seed/split_playbooks/*_templates.json`
5. Update Word playbooks if the user asks for "文档", "小文档", "playbook", or provides DOCX files.
6. For a new reply scenario, add the rule in this order: stage classification, runtime template, split JSON template, knowledge index keywords, Markdown playbook, then user-facing documentation.
7. Validate after edits, including Chinese search, pasted-image OCR fallback, and the affected scenario route.
8. When the command center consumes a changed catalog, validate JSON and template safety first, then update the approved catalog hash. Never approve a hash merely because the file changed.

## Fast Loading and UI Behavior

- Startup loads only `knowledge_index.json` and lightweight routing metadata.
- Load one split template file after classification; do not restore all-template startup loading.
- Search must work with Chinese or English terms such as `价格`, `售后`, `M7S`, `内测`, `维修`, `YouTube`, and `first showcase`.
- OCR must normalize pasted or recognized text before classification, preserve the original text for review, and show a recoverable error when recognition fails.
- Copy and Insert remain manual actions. Insert should target the active message composer and must not send the message.

## Validation

Use the bundled runtime if available:

```powershell
& "C:\Users\<your-user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" --check "<project>\src\app.js"
& "C:\Users\<your-user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" --check "<project>\src\stageRules.js"
& "C:\Users\<your-user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" --check "<project>\chrome-extension\contentScript.js"
```

Validate JSON files with Python or PowerShell. For DOCX updates, use `python-docx` structural validation and OOXML text scans. If LibreOffice/`soffice` is not installed, state that visual render QA was unavailable.

## Packaging Workflow

When the user asks to package this skill for other projects:

1. Build a clean skill folder containing:
   - `SKILL.md`
   - `references/ONE_FILE_GUIDE.md`
   - optional installer/check scripts
2. Package it as `varla-kol-reply-assistant.skill`.
3. Also provide a single standalone Chinese guide file outside the `.skill` package so the user can open it directly.
4. Include one-click folder link in the final response.

Read `references/ONE_FILE_GUIDE.md` when the user needs handoff or installation instructions.
