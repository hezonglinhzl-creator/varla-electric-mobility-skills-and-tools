# KOL Command Center App / KOL 邮件总控台程序

[简体中文](README.md) | **English**

A local WebUI, four mail groups, knowledge retrieval, reply review, confirmation and pause.

## Requirements

Windows, Python 3.11+ and separate Gmail/reply/contract/Feishu component setup.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Configure optional VARLA_KOL_DATA_DIR, VARLA_KOL_REPLY_ROOT and VARLA_KOL_EXPECTED_ACCOUNT, then your Gmail authorization. The default data directory is %LOCALAPPDATA%/VarlaKOLCommandCenter.
2. The original `START_KOL_COMMAND_CENTER.bat` relies on Codex's bundled Python; use the manual route below if unavailable.
3. Run `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.lock` here.
4. Run `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`.
5. Open the local URL and inspect system health before recognition. Resolve missing component setup first.

Open in your browser: `http://127.0.0.1:8791/`

## Expected result

Health checks show local/manual modes and actual component availability.

## Current limits

Background junk cleanup is disabled by default; only VARLA_ENABLE_JUNK_CLEANUP=true enables its timer. Recognition/manual cleanup can still mutate mail. config.example.json is reference-only; configure launch environment variables. Gmail files are gmail-credentials.json and gmail-token.json at the data root. Without business knowledge, the setup UI loads but replies require manual handling.

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
