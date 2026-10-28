# Gmail KOL 邮件自动化 / Gmail KOL Email Automation

**简体中文** | [English](README.en.md)

通过 Gmail OAuth 读取邮件、生成草稿并执行显式批准的发送，配套总控台可集中查看任务。

## 功能特性

- 账号核验与完整线程读取
- 默认草稿和发送前检查
- 线程回复、去重和审计记录

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| KOL 邮件总控台程序 | [varla-kol-command-center](../../apps/varla-kol-command-center/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### KOL 邮件总控台程序 (`varla-kol-command-center`)

Windows、Python 3.11+；Gmail/回复/合同/飞书组件需各自配置。

先进入 `../../apps/varla-kol-command-center`。本地 WebUI、四类邮件路由、知识检索、回复预览、人工确认与暂停。

1. 先配置可选环境变量 VARLA_KOL_DATA_DIR（数据目录）、VARLA_KOL_REPLY_ROOT（回复程序路径）和 VARLA_KOL_EXPECTED_ACCOUNT（核验邮箱），再准备自己的 Gmail 授权。默认数据目录为 %LOCALAPPDATA%/VarlaKOLCommandCenter。
2. 原一键入口是 `START_KOL_COMMAND_CENTER.bat`；它依赖本机 Codex 捆绑 Python，不存在时用下面的手动方式。
3. 手动：在本目录运行 `python -m venv .venv`，再运行 `.\.venv\Scripts\python.exe -m pip install -r requirements.lock`。
4. 运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`。
5. 打开本地地址，先看系统自检。配置缺失时先修复，不直接点击邮件识别。

本地地址：`http://127.0.0.1:8791/`

[查看完整程序与浏览器插件安装说明](../../apps/varla-kol-command-center/README.md)

公开分发版后台垃圾邮件清理默认关闭；仅设置 VARLA_ENABLE_JUNK_CLEANUP=true 才启动定时线程。识别/手动清理按钮仍可能修改邮箱。config.example.json 仅供参考，程序读取启动环境变量；Gmail OAuth 文件实际位于数据根目录 gmail-credentials.json 与 gmail-token.json。未提供业务知识时可打开设置界面，但回复必须转人工。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 你自己的 Gmail OAuth 客户端文件、令牌路径和邮件范围。 |
| 输出 | 核验结果、邮件预览、草稿或经授权发送后的回执。 |

```text
使用 varla-gmail-automation，先验证当前邮箱，只查最近 7 天的 KOL 邮件，生成草稿给我看，不发送。
```

## Gmail 初次授权

在本仓库的 `skill/varla-gmail-automation` 目录运行以下命令。先在自己的 Google Cloud 项目启用 Gmail API，创建桌面 OAuth 客户端，保存自己的 credentials.json；令牌路径放在 Git 仓库之外。把命令中的路径和邮箱改成自己的已授权邮箱。

```powershell
python -m pip install -r scripts/requirements.txt
python scripts/gmail_automation.py --credentials C:/secure/credentials.json --token C:/secure/gmail-token.json --expected-account operator@example.com authorize
python scripts/gmail_automation.py --credentials C:/secure/credentials.json --token C:/secure/gmail-token.json --expected-account operator@example.com verify
```

先核验邮箱，再按 `SKILL.md` 只读搜索或建草稿。真实发送需要 `--mode send --confirm SEND` 和准确的收件人、线程、正文授权。

## 当前限制与常见问题

仓库没有 OAuth 文件或邮箱内容。真实发送需要核对发件邮箱、收件人、线程和正文，并满足 CLI 发送保护。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
