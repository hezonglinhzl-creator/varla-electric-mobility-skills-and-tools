@echo off
cd /d "%~dp0"

set PYTHON_CMD=python
python --version >nul 2>nul
if errorlevel 1 set PYTHON_CMD=py

%PYTHON_CMD% "%~dp0viral_video_finder_server.py" --export-only
%PYTHON_CMD% "%USERPROFILE%\Documents\New project 9\项目\公共脚本和缓存\scripts\feishu_import_markdown_tables.py" "%~dp0outputs\viral_video_research_feishu.md" --title "外网爆款视频库 - 电摩选题"
pause
