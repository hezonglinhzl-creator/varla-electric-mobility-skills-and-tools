# KOL 邮件总控台程序 / KOL Command Center App

**简体中文** | [English](README.en.md)

本地 WebUI、四类邮件路由、知识检索、回复预览、人工确认与暂停。

## 运行环境

Windows、Python 3.11+；Gmail/回复/合同/飞书组件需各自配置。

## 第一次使用

先解压完整包。以下命令都在**当前程序目录**运行，不要在 ZIP 预览窗口中运行。Windows 用户可在资源管理器打开该目录，在地址栏输入 `powershell` 并按回车。

1. 先配置可选环境变量 VARLA_KOL_DATA_DIR（数据目录）、VARLA_KOL_REPLY_ROOT（回复程序路径）和 VARLA_KOL_EXPECTED_ACCOUNT（核验邮箱），再准备自己的 Gmail 授权。默认数据目录为 %LOCALAPPDATA%/VarlaKOLCommandCenter。
2. 原一键入口是 `START_KOL_COMMAND_CENTER.bat`；它依赖本机 Codex 捆绑 Python，不存在时用下面的手动方式。
3. 手动：在本目录运行 `python -m venv .venv`，再运行 `.\.venv\Scripts\python.exe -m pip install -r requirements.lock`。
4. 运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`。
5. 打开本地地址，先看系统自检。配置缺失时先修复，不直接点击邮件识别。

浏览器打开：`http://127.0.0.1:8791/`

## 成功后应该看到什么

自检显示本地模式、人工模式及各组件真实状态。

## 当前功能边界

公开分发版后台垃圾邮件清理默认关闭；仅设置 VARLA_ENABLE_JUNK_CLEANUP=true 才启动定时线程。识别/手动清理按钮仍可能修改邮箱。config.example.json 仅供参考，程序读取启动环境变量；Gmail OAuth 文件实际位于数据根目录 gmail-credentials.json 与 gmail-token.json。未提供业务知识时可打开设置界面，但回复必须转人工。

## 常见问题

| 现象 | 处理方法 |
| --- | --- |
| 黑窗口闪退 / 找不到 Python | 在当前目录打开 PowerShell，执行 `python --version`。需要安装时从 python.org 安装并勾选 Add Python to PATH，然后重新运行本文命令看具体错误。 |
| 提示缺少模块 | 用启动程序的同一个 Python 安装该程序 requirements 中的依赖。 |
| 页面打不开 / 端口占用 | 对照本文地址和服务日志；先关闭自己正在使用的冲突工具。浏览器扩展不能替代后端。 |
| Excel 保存失败 | 关闭 Excel/WPS 中的文件，检查输出路径后重试一次。 |
| 登录或飞书权限失败 | 使用自己的配置，检查目标资源权限；不要复制别人的 Token。 |

## 本地数据

账号配置、会话、台账和运行结果由使用者在自己电脑生成或配置。公开源码不附带真实客户/KOL 数据、邮箱内容、合同或已登录账号。
