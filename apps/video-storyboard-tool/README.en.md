# Local Shot Detection and Storyboards / 本地视频拆镜头与分镜表

[简体中文](README.md) | **English**

Upload videos, split shots, extract frames, edit storyboards and export tables.

## Requirements

Python 3.11+, FFmpeg/FFprobe; Whisper is optional for speech transcription.

## First run

Extract the whole package first. Run the steps below from **this program directory**, not from the ZIP preview. To open PowerShell here on Windows, open the folder in File Explorer, type `powershell` in its address bar and press Enter.

1. Run `python -m venv .venv` in this directory.
2. Run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. Check `ffmpeg -version`; install `requirements-whisper.txt` with the same Python only if transcription is needed.
4. Run `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787`.
5. Open the page, upload your short test video, review shots/transcripts, edit and export. Feishu needs your own `.env` settings.

Open in your browser: `http://127.0.0.1:8787`

## Expected result

Frames, JSON and tables appear under `outputs/<job_id>/`.

## Current limits

Some descriptions are templates/placeholders, not completed visual understanding. Transcripts may be empty without Whisper.

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
