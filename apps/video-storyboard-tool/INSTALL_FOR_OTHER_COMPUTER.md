# Local Video Storyboard Tool - Install Guide

This package is a local Windows video storyboard tool.

It supports:

- Uploading one or more short videos.
- Auto shot splitting.
- Frame extraction.
- Dialogue/subtitle mapping when Whisper/FFmpeg are available.
- Local table display and export.
- Feishu document native-table sync.
- Reference-generation mode for e-moto products.

## 1. Install Prerequisites

Install these first:

- Python 3.10 or newer
- FFmpeg, added to Windows PATH

Optional but recommended for better dialogue extraction:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-whisper.txt
```

Whisper/Torch can be large, so they are not installed by default.

## 2. Start

Double-click:

`START_HERE.bat`

Then open:

`http://127.0.0.1:8787/`

The first run creates `.venv`, installs packages, and creates `.env` from `.env.example`.

## 3. Feishu Setup

Open `.env` and fill your own values:

```env
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_USER_ACCESS_TOKEN=
FEISHU_DOC_URL=
FEISHU_WIKI_PARENT_URL=
FEISHU_ENABLE_SYNC=true
```

The tool writes to a normal Feishu document/wiki document. It appends content to the end and should not overwrite existing content.

Required Feishu permissions usually include:

- tenant access token
- docx document read/write
- wiki read if using a wiki link
- media/file upload for images

The Feishu app must be able to access the target document. Add the app/bot as a collaborator if needed.

## 4. Important Safety Notes

This package intentionally excludes:

- `.env`
- `.venv`
- generated `outputs`
- `logs`
- `cache_reports`
- uploaded videos

Do not share `.env`; it contains private credentials.

## 5. Troubleshooting

If the page opens but dialogue is empty:

- Install FFmpeg.
- Install optional Whisper requirements.

If Feishu sync fails:

- Check the newest `logs/sync_*.json`.
- `131005 not found` usually means wrong document/wiki link or app access.
- `1770001 invalid param` usually means a Feishu Docx block payload issue.

If local thumbnails are gray:

- Check whether `outputs/<job_id>/frames/shot_xxx.jpg` exists.
- Do not clean current batch frames before sync is finished.
