# Gmail KOL Email Automation / Gmail KOL 邮件自动化

[简体中文](README.md) | **English**

Use Gmail OAuth to read threads, prepare drafts and perform explicitly approved sends, with an optional command-center UI.

## Features

- Account verification and full-thread reads
- Draft defaults and pre-send checks
- Thread replies, idempotency and audit records

## What is included

| Part | Location |
| --- | --- |
| KOL Command Center App | [varla-kol-command-center](../../apps/varla-kol-command-center/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### KOL Command Center App (`varla-kol-command-center`)

Windows, Python 3.11+ and separate Gmail/reply/contract/Feishu component setup.

Open `../../apps/varla-kol-command-center` first. A local WebUI, four mail groups, knowledge retrieval, reply review, confirmation and pause.

1. Read `README_使用说明.md` and configure your Gmail authorization and component locations.
2. The original `START_KOL_COMMAND_CENTER.bat` relies on Codex's bundled Python; use the manual route below if unavailable.
3. Run `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.lock` here.
4. Run `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`.
5. Open the local URL and inspect system health before recognition. Resolve missing component setup first.

Local URL: `http://127.0.0.1:8791/`

[Full program / browser-extension guide](../../apps/varla-kol-command-center/README.en.md)

Recognition includes narrowly scoped vendor-junk handling that can mutate Gmail; read the detailed rules. Review component paths in app/config.py and related files. Replace the your-workspace Feishu hostname placeholder in app/web/app.js with your tenant hostname before opening those resource links.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Your Gmail OAuth client file, token path and requested mail scope. |
| Output | Verification results, previews, drafts or receipts for authorized sends. |

```text
Use varla-gmail-automation to verify the mailbox, read only KOL mail from the last seven days and prepare drafts without sending.
```

## Gmail authorization

Run the following inside `skill/varla-gmail-automation`. Enable Gmail API in your own Google Cloud project, create a Desktop OAuth client and save your credentials.json. Keep tokens outside Git and replace paths/account with your own authorized mailbox.

```powershell
python -m pip install -r scripts/requirements.txt
python scripts/gmail_automation.py --credentials C:/secure/credentials.json --token C:/secure/gmail-token.json --expected-account operator@example.com authorize
python scripts/gmail_automation.py --credentials C:/secure/credentials.json --token C:/secure/gmail-token.json --expected-account operator@example.com verify
```

Verify the mailbox first, then follow SKILL.md for scoped reads or drafts. Real sends need `--mode send --confirm SEND` and authorization for the exact recipient, thread and content.

## Limits and troubleshooting

No OAuth files or mailbox data are included. A real send must verify account, recipient, thread and content and satisfy the CLI send guard.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
