@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: creating virtual environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8787'"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8787
