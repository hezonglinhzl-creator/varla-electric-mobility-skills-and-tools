---
name: varla-kol-reply-assistant
description: Maintain, tune, and package a Varla/Himiway KOL reply assistant for Chrome. Use when the task involves a floating in-page KOL widget, reply template logic, OCR screenshot paste or drag handling, Meta Business Suite / Instagram / TikTok / Gmail support, product-exchange reply rules, or a project structured like C:/path/to/your-project
---

# Varla KOL Reply Assistant

Maintain the Chrome extension as the main product surface.

## Project Path

Default project path on Team Member's machine:

`C:/path/to/your-project`

Default extension path on Team Member's machine:

`C:/path/to/your-project`

If the project is installed elsewhere, search for these files first:

- `chrome-extension/contentScript.js`
- `chrome-extension/manifest.json`
- `knowledge_seed/templates.json`

## Workflow

1. Preserve the user rule: never batch-delete files or directories.
2. Treat the floating in-page widget as the main product. The local web UI is fallback only.
3. Keep the launcher small, draggable, and safe to click. Regular click should expand; drag should move.
4. Keep generated replies as 6 options by default: Natural 2, Formal 2, Short 2.
5. Keep reply results inside one overall collapsible section that is open by default.
6. Never auto-send messages. Insert only when the user clicks `Insert`.
7. Prefer short, natural DM copy for Instagram, TikTok, and Meta Business Suite. Prefer structured professional copy for Gmail.
8. Keep product specs, campaign terms, and shipping timing conservative. Do not invent details.
9. Keep OCR local through bundled Tesseract assets. Do not upload screenshots to outside services by default.
10. When packaging the skill, include `agents/openai.yaml` and validate before export.
11. For shared copies, keep path guidance generic and treat Team Member's Windows paths as defaults, not requirements.

## Current Product Rules

- First collaboration model: product exchange by default.
- Commission: possible for stronger creators, commonly `8%` if approved.
- Bike positioning:
  - `M5S`: default first-stage creator bike
  - `M7S`: stronger-fit / performance-oriented creators after approval
- Posting rules commonly referenced in replies:
  - draft approval before posting
  - Instagram collaborator: `@varla_adventure`
  - TikTok tag/mention: `@varla_sport`
  - approved posts should stay live unless Varla approves changes

## Read These References When Needed

- For feature map, OCR flow, launcher behavior, and key file routing: read `references/chrome-extension-map.md`.
- For reply rules, templates, product canon, and current internal playbook guidance: read `references/reply-engine.md`.

## Key Files

- `chrome-extension/contentScript.js`: main floating widget, OCR, reply generation, insert flow
- `chrome-extension/manifest.json`: Chrome MV3 permissions and resource exposure
- `chrome-extension/vendor/`: bundled Tesseract assets
- `chrome-extension/popup.js`: legacy popup logic
- `knowledge_seed/templates.json`: local editable templates
- `knowledge_seed/product_specs.json`: product canon and confirmed specs
- `knowledge_seed/Varla_KOL_常见问题回复库.md`: internal common-question bank
- `tools/serve_ui.ps1`: fallback local preview; avoid port `8766`

## Validation

Run these after edits:

```powershell
node --check "C:/path/to/your-project"
node --check "C:/path/to/your-project"
Get-Content -LiteralPath "C:/path/to/your-project" -Encoding UTF8 | ConvertFrom-Json | Out-Null
```

Validate the skill itself after updates when the environment has `yaml` available:

```powershell
python "C:\Users\<your-user>\.codex\skills\.system\skill-creator\scripts\quick_validate.py" "C:\Users\<your-user>\.codex\skills\varla-kol-reply-assistant"
```
