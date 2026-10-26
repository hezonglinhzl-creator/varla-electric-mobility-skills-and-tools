# Varla KOL Command Center / Varla KOL 邮件总控台

[简体中文](README.md) | **English**

A local dashboard for KOL mail classification, knowledge retrieval, reply previews and component health checks.

## Features

- KOL, pre-sales, logistics and after-sales groups
- Previews, manual confirmation and pause
- Local knowledge with low-frequency Feishu checks

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
| Input | Local Gmail, reply-assistant, contract and Feishu component setup. |
| Output | Local task lists, replies for review and execution audits. |

```text
Use varla-kol-command-center to inspect health and component setup first; do not scan or mutate the mailbox.
```


## Limits and troubleshooting

A new machine needs component-path setup. Recognition/junk cleanup can mutate the mailbox; read the detailed program guide first. A loaded page does not prove integrations work.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
