# eMoto AI Content Resources and Validation / 电摩 AI 内容资料与验证工具

[简体中文](README.md) | **English**

Story-director and product-video resources with prompt-structure validation.

## Requirements

Codex, with optional Python for prompt-file validation.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. This is a content-resource toolkit. Use `安装Skill.cmd` at the complete bundle root first.
2. Give Codex your product references and verified specs, then invoke emoto-ugc-story-director.
3. Review the shots/prompts before choosing your own rendering platform.
4. For structure validation run `python skills/emoto-ugc-story-director/scripts/validate_prompt.py C:/path/prompt.md`.

## Expected result

Reviewable shots/prompts and a structure-check result from the validator.

## Current limits

No standalone desktop renderer or preconfigured generation account is included.

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
