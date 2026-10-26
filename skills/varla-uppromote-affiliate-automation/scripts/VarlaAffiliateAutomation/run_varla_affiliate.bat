@echo off
chcp 65001 >nul
setlocal
set "VARLA_PYTHON=%LOCALAPPDATA%\VarlaKOLCommandCenter\runtime\venv\Scripts\python.exe"
if not exist "%VARLA_PYTHON%" set "VARLA_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "NODE_PATH=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

if not "%~1"=="" (
  "%VARLA_PYTHON%" "%~dp0varla_affiliate.py" %*
  goto done
)

echo Varla UpPromote Affiliate 全流程自动化
echo 请先打开 AdsPower，并保持 Shopify / UpPromote 已登录。
echo.
set /p "FEISHU_URL=粘贴飞书 Base 链接: "
set /p "KOL_NAME=输入 KOL Name（例如 Big Tdtto）: "
set /p "EMAIL_MODE=输入 DRAFT 只建草稿，或 SEND 直接发送: "

if /I "%EMAIL_MODE%"=="SEND" (
  echo 即将从 info@varlascooter.com 发送无附件邮件。
  set /p "SEND_CONFIRM=确认请输入 SEND: "
  "%VARLA_PYTHON%" "%~dp0varla_affiliate.py" --feishu-url "%FEISHU_URL%" --kol-name "%KOL_NAME%" --send --confirm "%SEND_CONFIRM%"
) else (
  "%VARLA_PYTHON%" "%~dp0varla_affiliate.py" --feishu-url "%FEISHU_URL%" --kol-name "%KOL_NAME%"
)

:done
echo.
pause
