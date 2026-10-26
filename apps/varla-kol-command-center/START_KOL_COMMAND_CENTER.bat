@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_server.ps1"
if errorlevel 1 (
  echo.
  echo Varla KOL Command Center could not start. Please review the message above.
  pause
  exit /b 1
)
endlocal
