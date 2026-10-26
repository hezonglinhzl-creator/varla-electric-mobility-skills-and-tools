# Social Reporting Templates / 社媒周报模板资料

[简体中文](README.md) | **English**

Platform aggregation, date checks and weekly/monthly reporting instructions.

## Requirements

Codex and your own screenshots/CSV.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. This directory contains templates/skill resources, with no server to start.
2. Run `安装Skill.cmd` at the full bundle root and reopen Codex.
3. Provide your date ranges, screenshots and CSV and invoke 周报skill with the required platform scope.
4. Review dates, metric definitions and missing data before using the tables.

## Expected result

Reports and paste-ready tables are saved to your chosen local location.

## Current limits

No business screenshots/data or automatic dashboard login are included.

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
