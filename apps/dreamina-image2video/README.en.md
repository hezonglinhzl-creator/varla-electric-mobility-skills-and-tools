# Dreamina Image-to-Video Command Wrapper / 即梦图生视频命令包装器

[简体中文](README.md) | **English**

Build CLI commands from JSON jobs, default to dry-run and execute only with --execute.

## Requirements

Python and your own Dreamina CLI/login; command previews do not require generation.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Install image2-motion-agent. The wrapper is `image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py`.
2. Create your job.json with image, prompt, duration, poll and video_resolution.
3. First run `python image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py --job C:/path/job.json`.
4. Check `will_consume_credits: false` and review the prompts.
5. Before real generation, inspect `dreamina -h` for your installed version and log in. Add `--execute` only after explicit approval of the same job.

## Expected result

A preview returns the command array and credit-use flag; execution returns the CLI result.

## Current limits

You manage the third-party CLI version and credits; no account or free credits are provided.

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
