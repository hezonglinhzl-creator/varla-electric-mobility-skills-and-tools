# Product Video Breakdown and Storyboard Adaptation / 产品视频拆解与分镜复刻

[简体中文](README.md) | **English**

Generate frames and storyboards with the local shot tool, then use the skill to adapt products, characters, prompts and social copy.

## Features

- Shot detection and keyframes
- CSV / Excel / Markdown exports
- Product substitution and eMoto UGC planning

## What is included

| Part | Location |
| --- | --- |
| Local Shot Detection and Storyboards | [video-storyboard-tool](../../apps/video-storyboard-tool/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### Local Shot Detection and Storyboards (`video-storyboard-tool`)

Python 3.11+, FFmpeg/FFprobe; Whisper is optional for speech transcription.

Open `../../apps/video-storyboard-tool` first. Upload videos, split shots, extract frames, edit storyboards and export tables.

1. Run `python -m venv .venv` in this directory.
2. Run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. Check `ffmpeg -version`; install `requirements-whisper.txt` with the same Python only if transcription is needed.
4. Run `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787`.
5. Open the page, upload your short test video, review shots/transcripts, edit and export. Feishu needs your own `.env` settings.

Local URL: `http://127.0.0.1:8787`

[Full program / browser-extension guide](../../apps/video-storyboard-tool/README.en.md)

Some descriptions are templates/placeholders, not completed visual understanding. Transcripts may be empty without Whisper.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | A reference video you may use, product images, specifications and target platform. |
| Output | Keyframes, editable shot tables, adapted scripts and generation prompts. |

```text
Use viral-product-video-replicator to break down my reference into shots, export a table, then propose an eMoto adaptation preserving product shape and specifications.
```


## Limits and troubleshooting

Speech transcription needs optional Whisper and FFmpeg. Some descriptions are templates/placeholders and need review; Feishu sync requires your permissions.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
