@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  echo Install Python 3.10+ first, then run this file again.
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo [WARN] FFmpeg was not found in PATH.
  echo Video upload and frame extraction may still work, but audio transcription can fail.
  echo Install FFmpeg if you need dialogue extraction.
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [INFO] Created .env from .env.example. Fill Feishu values in .env if sync is needed.
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating local Python virtual environment...
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"
echo [INFO] Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [INFO] Starting local video storyboard tool...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8787/'"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
