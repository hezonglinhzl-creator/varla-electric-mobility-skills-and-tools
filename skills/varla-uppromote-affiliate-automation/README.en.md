# UpPromote KOL Affiliate Workflow / UpPromote KOL 联盟流程

[简体中文](README.md) | **English**

Start from a Feishu creator record and verify affiliate details, coupons, links and email stages using the current browser state.

## Features

- Exact record/email matching
- Coupon and existing-link deduplication
- Dry runs, email drafts and stage recovery

## What is included

| Part | Location |
| --- | --- |
| Shopify KOL Browser Order Tool | [shopify-order-bot](../../apps/shopify-order-bot/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

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
| Input | Your Base/record URL, exact code, AdsPower session and service configuration. |
| Output | Verified codes/links, Feishu readbacks and email drafts or receipts. |

```text
Use varla-uppromote-affiliate-automation to dry-run my record, check existing codes/links and report missing setup without creating records or sending mail.
```

## Start with read-only validation

Run inside `skill/varla-uppromote-affiliate-automation` after configuring your Feishu/browser environment. Replace the placeholder with a URL you may access.

```powershell
python scripts/run_varla_affiliate.py --feishu-url "YOUR_FEISHU_BASE_URL" --code-name "YOUR_APPROVED_CODE" --dry-run
```

## Limits and troubleshooting

Requires your Feishu, AdsPower, Shopify/UpPromote and Gmail setup. Coupon rules must follow currently confirmed policy.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
