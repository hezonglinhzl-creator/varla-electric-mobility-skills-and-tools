# Local Short Video Score Analyzer / 本地短视频评分分析

[简体中文](README.md) | **English**

Opening-hook checks, pacing, frames, waveforms and heuristic score exports.

## Requirements

Python 3.11+, FFmpeg/FFprobe and Pillow.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Run `python -m pip install -r requirements.txt`.
2. Check `ffmpeg -version` and `ffprobe -version`.
3. Run `start_video_score_analyzer.bat` or `python server.py`.
4. Open the page, upload your video, inspect scores/frames/suggestions and export the report.

Open in your browser: `http://127.0.0.1:8765`

## Expected result

Exports are in `exports/`; intermediate analysis is in `reports/`.

## Current limits

Scores are heuristic guidance, not ad-performance predictions. Port 8765 conflicts with the KOL recorder; avoid running both simultaneously.

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
