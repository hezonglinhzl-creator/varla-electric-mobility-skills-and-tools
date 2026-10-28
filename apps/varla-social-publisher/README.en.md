# Social Scheduling and Mock Publishing Prototype / 社媒排期与模拟发布原型

[简体中文](README.md) | **English**

A local dashboard, task validation, BullMQ worker and mock adapter.

## Requirements

Node.js 22, npm and Redis; Docker may provide Redis/MinIO, with FFmpeg for media.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Install system Node.js 22+ and run npm install in this program folder.
2. Run START_VARLA.bat for the static dashboard, or powershell -File tools/start_varla.ps1 -CheckOnly for a non-starting diagnostic.
3. Redis and the worker do not start automatically. To develop the mock worker, supply your Redis and explicitly configure RUN_WORKER, MOCK_PUBLISHING and REDIS_URL.
4. The page has no upload/review/scheduling workflow. /api/health is a fixed 503 placeholder, not a real dependency check.

Open in your browser: `http://127.0.0.1:3000`

## Expected result

The current page is a static dashboard prototype. `/api/health` always returns a 503 placeholder and does not probe dependencies. Validation and the mock worker can be developed separately; the UI has no complete upload/scheduling workflow.

## Current limits

The launcher starts only the dashboard with system Node.js 22+ and never starts a worker automatically. Install npm dependencies first; inspect readiness with `powershell -File tools/start_varla.ps1 -CheckOnly`. Real adapters, OAuth, app review and an upload/scheduling workflow remain unimplemented.

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
