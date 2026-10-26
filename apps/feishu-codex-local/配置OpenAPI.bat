@echo off
set "PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PY%" (
  "%PY%" "%~dp0scripts\feishu_docs.py" configure
) else (
  python "%~dp0scripts\feishu_docs.py" configure
)
pause
