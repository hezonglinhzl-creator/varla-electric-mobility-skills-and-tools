# UpPromote KOL affiliate automation

This script uses the configured AdsPower Shopify profile, the approved local
Feishu OpenAPI configuration, and the local Varla Gmail sender.

It processes exactly one Feishu record, found by its exact email, KOL name, or code name. It
does not import a batch and does not submit anything until `--apply` is given.

## 1. Preview only

```powershell
cd "C:\Users\<your-user>\Documents\电摩项目"
$env:PYTHONPATH = "C:\Users\<your-user>\Documents\电摩项目"
& ".\shopify_order_bot\.venv\Scripts\python.exe" .\shopify_order_bot\up_promote_affiliate_rpa.py --email "creator@example.com"
```

Review the printed name, email, code, and current code link. A non-empty link
means the browser flow will be skipped.

## 2. Create and write back

```powershell
& ".\shopify_order_bot\.venv\Scripts\python.exe" .\shopify_order_bot\up_promote_affiliate_rpa.py --email "creator@example.com" --apply
```

For a record without a link, this creates or reuses the UpPromote affiliate,
sets the `KOL - $100` program, coupon/path, collection destination, saves a
short link, and verifies the Feishu `code link` write-back.

## 3. Send only after the write-back succeeds

```powershell
& ".\shopify_order_bot\.venv\Scripts\python.exe" .\shopify_order_bot\up_promote_affiliate_rpa.py --email "creator@example.com" --apply --send --confirm SEND
```

The sender is fixed to `info@varlascooter.com`. The script stops if the
standard Gmail sender safeguards fail.
