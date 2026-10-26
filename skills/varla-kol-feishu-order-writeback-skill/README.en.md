# KOL Order Feishu Writeback / KOL 订单飞书回写

[简体中文](README.md) | **English**

Write verified Shopify order numbers and KOL codes/Impact IDs to the specified Feishu records and read them back.

## Features

- Email-first exact matching
- Narrow order-field updates
- Readback verification

## What is included

| Part | Location |
| --- | --- |
| Local Feishu OpenAPI Toolkit | [feishu-codex-local](../../apps/feishu-codex-local/README.en.md) |
| Shopify KOL Browser Order Tool | [shopify-order-bot](../../apps/shopify-order-bot/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### Local Feishu OpenAPI Toolkit (`feishu-codex-local`)

Windows, Python and your Feishu app permissions; chat bridging is optional.

Open `../../apps/feishu-codex-local` first. Documents, native tables, Base records and attachments, with setup/check scripts.

1. Run `配置OpenAPI.bat` and enter your own App ID and App Secret.
2. Configuration stays locally at `%USERPROFILE%\.feishu-docs\config.json`.
3. Run `检查OpenAPI.bat`; add required permissions and publish your app version in Feishu if needed.
4. Run `python scripts/feishu_docs.py --help`, or ask Codex with the installed skill to read a specified document first.
5. Only chat-to-Codex bridging needs the separate bridge installation/configuration and cc-connect. OpenAPI data operations can run independently.

[Full program / browser-extension guide](../../apps/feishu-codex-local/README.en.md)

Unauthorized resources remain inaccessible. Do not upload your config or treat a failed check as a successful sync.

### Shopify KOL Browser Order Tool (`shopify-order-bot`)

Python 3.11+, AdsPower Local API and your Shopify admin access.

Open `../../apps/shopify-order-bot` first. Single-order Excel validation, address checks, fill and a separate submit step.

1. Run `python -m pip install -r requirements.txt`, then `python -m playwright install chromium`.
2. Copy `.env.example` to `.env` and enter your AdsPower API settings, profile ID and SHOPIFY_ADMIN_URL.
3. Prepare `KOL_order.xlsx` using this folder's documented headers; start with one synthetic test row.
4. Run `python main.py --step adspower`, then `python main.py --step browser` and log in to your own profile.
5. Run `python main.py --step fill` and review before submission. Execute real submission only when explicitly authorized.

[Full program / browser-extension guide](../../apps/shopify-order-bot/README.en.md)

Private configuration, login sessions and order workbooks must be supplied by the operator.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Current Feishu Base link, confirmed order results and update scope. |
| Output | Creator/order mappings, update receipts and readback results. |

```text
Use varla-kol-feishu-order-writeback-skill to read my Base, match this confirmed order by email and show proposed field changes before writing.
```


## Limits and troubleshooting

Do not guess records from row position or names. Order creation and shipment are separate facts; update status only when confirmed.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
