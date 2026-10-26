# Shopify KOL Browser Order Tool / Shopify KOL 订单浏览器工具

[简体中文](README.md) | **English**

Single-order Excel validation, address checks, fill and a separate submit step.

## Requirements

Python 3.11+, AdsPower Local API and your Shopify admin access.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Run `python -m pip install -r requirements.txt`, then `python -m playwright install chromium`.
2. Copy `.env.example` to `.env` and enter your AdsPower API settings, profile ID and SHOPIFY_ADMIN_URL.
3. Prepare `KOL_order.xlsx` using this folder's documented headers; start with one synthetic test row.
4. Run `python main.py --step adspower`, then `python main.py --step browser` and log in to your own profile.
5. Run `python main.py --step fill` and review before submission. Execute real submission only when explicitly authorized.

## Expected result

The intended order form is filled and the CLI reports checks; this does not buy a shipping label.

## Current limits

Private configuration, login sessions and order workbooks must be supplied by the operator.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| Window closes / Python missing | Open PowerShell in this directory, run `python --version`, install Python from python.org with Add Python to PATH if needed, then rerun the documented command. |
| Missing module | Install the program's requirements using the same Python executable used to launch it. |
| Page does not open / port occupied | Check the URL and service log; stop your own conflicting tool before retrying. A browser extension cannot replace its local backend. |
| Workbook cannot be saved | Close the file in Excel/WPS, verify the output path and retry once. |
| Account or Feishu permission failure | Use your own configuration and check resource permissions. Do not copy another person's tokens. |

## Local data

Your credentials, browser sessions, workbooks and outputs are created/configured locally. The public source does not include real customer/creator records, mailboxes, contracts or logged-in accounts.
