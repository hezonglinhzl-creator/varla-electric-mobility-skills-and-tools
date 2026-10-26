# Bundled Video Storyboard Tool

The file `video-storyboard-tool-portable.zip` is the portable source package for the Windows local video storyboard and Feishu synchronization tool.

## Install

1. Extract the ZIP to a writable folder.
2. Install Python 3.10 or newer.
3. Install FFmpeg and add it to PATH when dialogue extraction is needed.
4. Double-click `START_HERE.bat`.
5. Open `http://127.0.0.1:8787/` if the browser does not open automatically.

The first launch creates `.venv`, installs `requirements.txt`, and creates a blank local `.env` from `.env.example`.

## Security

The package excludes `.env`, access tokens, app secrets, logs, uploaded videos, generated outputs, and the original computer's `.venv`.

Enter the current Feishu document or Wiki URL in the application's interface for each run. Do not rely on a fixed document link.
