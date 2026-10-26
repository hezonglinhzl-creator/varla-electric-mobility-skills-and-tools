# Local Feishu OpenAPI Toolkit / 飞书本地 OpenAPI 工具包

[简体中文](README.md) | **English**

Documents, native tables, Base records and attachments, with setup/check scripts.

## Requirements

Windows, Python and your Feishu app permissions; chat bridging is optional.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Run `配置OpenAPI.bat` and enter your own App ID and App Secret.
2. Configuration stays locally at `%USERPROFILE%\.feishu-docs\config.json`.
3. Run `检查OpenAPI.bat`; add required permissions and publish your app version in Feishu if needed.
4. Run `python scripts/feishu_docs.py --help`, or ask Codex with the installed skill to read a specified document first.
5. Only chat-to-Codex bridging needs the separate bridge installation/configuration and cc-connect. OpenAPI data operations can run independently.

## Expected result

The checker reports real authorization status and a read task returns the requested document/fields.

## Current limits

Unauthorized resources remain inaccessible. Do not upload your config or treat a failed check as a successful sync.

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
