# KOL Reply Assistant and Local Plugin / KOL 网页回复助手与本地插件

[简体中文](README.md) | **English**

Generate copyable creator replies in a browser panel and include a shareable instruction copy of the original Varla KOL reply plugin.

## Features

- Chrome floating reply panel
- Six options across casual, formal and short groups
- Manual ChatGPT handoff and the local three-option reply plugin

## What is included

| Part | Location |
| --- | --- |
| KOL Browser Reply Extension | [varla-kol-reply-program](../../apps/varla-kol-reply-program/README.en.md) |
| KOL Command Center App | [varla-kol-command-center](../../apps/varla-kol-command-center/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### KOL Browser Reply Extension (`varla-kol-reply-program`)

Chrome/Edge; the optional local-window mode requires Python.

Open `../../apps/varla-kol-reply-program` first. A floating KOL panel, message reading, six grouped replies, manual copy and a ChatGPT prompt.

1. Load the Chrome extension folder below containing manifest.json.
2. Open Instagram, TikTok, Meta Business Suite or Gmail and refresh existing tabs.
3. Open the KOL panel, select a message, use Read and check platform, stage, tone and product.
4. Generate six replies, verify current product/policy facts and copy one manually.
5. For ChatGPT, generate/copy the prompt and paste it yourself. The fallback local window starts with `program/varla-kol-reply-assistant/打开UI.bat`.

[Full program / browser-extension guide](../../apps/varla-kol-reply-program/README.en.md)

Templates may contain historical product facts; verify them against current knowledge. It assists drafting/copying and does not send automatically.

### KOL Command Center App (`varla-kol-command-center`)

Windows, Python 3.11+ and separate Gmail/reply/contract/Feishu component setup.

Open `../../apps/varla-kol-command-center` first. A local WebUI, four mail groups, knowledge retrieval, reply review, confirmation and pause.

1. Configure optional VARLA_KOL_DATA_DIR, VARLA_KOL_REPLY_ROOT and VARLA_KOL_EXPECTED_ACCOUNT, then your Gmail authorization. The default data directory is %LOCALAPPDATA%/VarlaKOLCommandCenter.
2. The original `START_KOL_COMMAND_CENTER.bat` relies on Codex's bundled Python; use the manual route below if unavailable.
3. Run `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.lock` here.
4. Run `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`.
5. Open the local URL and inspect system health before recognition. Resolve missing component setup first.

Local URL: `http://127.0.0.1:8791/`

[Full program / browser-extension guide](../../apps/varla-kol-command-center/README.en.md)

Background junk cleanup is disabled by default; only VARLA_ENABLE_JUNK_CLEANUP=true enables its timer. Recognition/manual cleanup can still mutate mail. config.example.json is reference-only; configure launch environment variables. Gmail files are gmail-credentials.json and gmail-token.json at the data root. Without business knowledge, the setup UI loads but replies require manual handling.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Creator message, platform, cooperation stage and verified product information. |
| Output | Reply options and prompts for manual copying; it does not press Send for you. |

```text
Use Varla KOL Reply to draft three short English replies to this sponsorship request. Do not promise a bike; ask for profile links, average views and audience countries.
```


## Limits and troubleshooting

The Chrome extension and Codex instruction plugin are separate entry points. The former has a webpage panel; the latter provides three replies in chat. Source copies do not transfer cloud identity or accounts.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
