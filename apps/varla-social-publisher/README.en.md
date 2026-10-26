# Social Scheduling and Mock Publishing Prototype / 社媒排期与模拟发布原型

[简体中文](README.md) | **English**

A local dashboard, task validation, BullMQ worker and mock adapter.

## Requirements

Node.js 22, npm and Redis; Docker may provide Redis/MinIO, with FFmpeg for media.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Open PowerShell here, run `Copy-Item .env.example .env`, set your local secrets and keep `MOCK_PUBLISHING=true`.
2. Run `npm install`, then `npm run db:generate` and `npm run db:push`.
3. Start Redis, check REDIS_URL in `.env`, then run `npm run dev`.
4. In another terminal run `$env:RUN_WORKER='true'; $env:MOCK_PUBLISHING='true'; $env:REDIS_URL='redis://127.0.0.1:6379'; npm run worker`.
5. Open the dashboard for mock jobs only. Resolve database, Redis, storage and worker health failures first.

Open in your browser: `http://127.0.0.1:3000`

## Expected result

Use the dashboard and mock jobs to inspect the workflow; `/api/health` reports dependency readiness.

## Current limits

Source rejects unconfigured real adapters. Meta/TikTok publishing, OAuth, app review and public media URLs still need integration; mock success is not a live publication.

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
