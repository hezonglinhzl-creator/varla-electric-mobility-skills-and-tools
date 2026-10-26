@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_desktop_launcher.ps1" -ProjectRoot "%~dp0"
if errorlevel 1 (
  echo.
  echo Varla KOL desktop launcher could not be installed.
  pause
  exit /b 1
)
echo.
echo Varla KOL desktop launcher is ready.
pause
endlocal
