@echo off
chcp 65001 >nul
title Install viral-product-video-replicator skill
echo.
echo Installing viral-product-video-replicator skill...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"
echo.
echo Done. If Codex is open, restart Codex to load the skill.
echo.
pause
