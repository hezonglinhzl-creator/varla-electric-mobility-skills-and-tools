@echo off
setlocal
cd /d "%~dp0"

set "PORT=8787"
set "URL=http://127.0.0.1:%PORT%/"

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
  start "" "%URL%"
  exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment not found.
  echo Please run START_HERE.bat once in:
  echo %CD%
  pause
  exit /b 1
)

if not exist "outputs" (
  mkdir "outputs"
)

set "PATH=%CD%\.venv\Scripts;%PATH%"
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%URL%'"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
