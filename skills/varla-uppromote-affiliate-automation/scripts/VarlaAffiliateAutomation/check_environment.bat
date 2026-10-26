@echo off
chcp 65001 >nul
setlocal
set "VARLA_PYTHON=%LOCALAPPDATA%\VarlaKOLCommandCenter\runtime\venv\Scripts\python.exe"
if not exist "%VARLA_PYTHON%" set "VARLA_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
"%VARLA_PYTHON%" "%~dp0check_environment.py"
echo.
pause
