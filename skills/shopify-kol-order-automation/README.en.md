# Shopify KOL Order Entry Automation / Shopify KOL 订单填写工具

[简体中文](README.md) | **English**

Use AdsPower and browser UI automation to fill KOL orders, verify inputs and submit only within authorized scope.

## Features

- Excel field validation
- Browser-session reuse and address checks
- Fill-only default with a separate submission step

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
| Input | Your KOL_order.xlsx, store admin URL and AdsPower profile. |
| Output | A filled order form and validation result; authorized runs may create an order. |

```text
Use shopify-kol-order-automation to validate my test order, run fill only and stop before submission for review.
```


## Limits and troubleshooting

Creating an order does not ship it or buy a label. Address conflicts, captchas and account mismatches stop the workflow.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
