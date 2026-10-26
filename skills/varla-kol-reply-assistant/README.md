# KOL 网页回复助手与本地插件 / KOL Reply Assistant and Local Plugin

**简体中文** | [English](README.en.md)

在创作者消息页面生成可复制的回复，并提供原有 Varla KOL 回复插件的可分享指令副本。

## 功能特性

- Chrome 网页侧边回复面板
- 自然、正式、简短三类共 6 条回复
- ChatGPT 手动桥接与本地三选回复插件

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| KOL 网页回复 Chrome 插件 | [varla-kol-reply-program](../../apps/varla-kol-reply-program/README.md) |
| KOL 邮件总控台程序 | [varla-kol-command-center](../../apps/varla-kol-command-center/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### KOL 网页回复 Chrome 插件 (`varla-kol-reply-program`)

Chrome/Edge；备用本地窗口需要 Python。

先进入 `../../apps/varla-kol-reply-program`。网页右侧 KOL 面板、消息读取、6 条分组回复、手动复制和 ChatGPT Prompt。

1. 加载下方包含 manifest.json 的 Chrome 扩展目录。
2. 打开 Instagram、TikTok、Meta Business Suite 或 Gmail；刷新已有页面。
3. 点击右侧 KOL 按钮，选中消息后点“读取”，确认平台、阶段、语气和产品。
4. 点“生成 6 条回复”，核对当前产品和政策后手动复制。
5. 需要 ChatGPT 时点 Generate ChatGPT Prompt / Copy Prompt，再自己粘贴；备用本地窗口入口是 `program/varla-kol-reply-assistant/打开UI.bat`。

[查看完整程序与浏览器插件安装说明](../../apps/varla-kol-reply-program/README.md)

模板可能包含历史产品事实，使用前必须按当前知识核对；它只辅助生成和复制，不自动发送。

### KOL 邮件总控台程序 (`varla-kol-command-center`)

Windows、Python 3.11+；Gmail/回复/合同/飞书组件需各自配置。

先进入 `../../apps/varla-kol-command-center`。本地 WebUI、四类邮件路由、知识检索、回复预览、人工确认与暂停。

1. 先读本目录 `README_使用说明.md`，配置自己的 Gmail 授权和外部组件位置。
2. 原一键入口是 `START_KOL_COMMAND_CENTER.bat`；它依赖本机 Codex 捆绑 Python，不存在时用下面的手动方式。
3. 手动：在本目录运行 `python -m venv .venv`，再运行 `.\.venv\Scripts\python.exe -m pip install -r requirements.lock`。
4. 运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8791`。
5. 打开本地地址，先看系统自检。配置缺失时先修复，不直接点击邮件识别。

本地地址：`http://127.0.0.1:8791/`

[查看完整程序与浏览器插件安装说明](../../apps/varla-kol-command-center/README.md)

识别中包含受限的营销垃圾邮件处理，可能修改邮箱；先读详细规则。迁移时要检查 app/config.py 等文件中的组件路径；app/web/app.js 的 your-workspace 飞书域名占位符需换为自己的域名，才能打开相应资源链接。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 创作者原消息、平台、合作阶段和已核实产品信息。 |
| 输出 | 待复制的英文回复及提示词，不会替你按发送。 |

```text
使用 Varla KOL 回复，针对这条 sponsorship 询问给 3 个简短英文回复：不承诺送车，索要主页、平均播放和受众国家。
```


## 当前限制与常见问题

Chrome 扩展与 Codex 指令插件是两种入口；前者有网页面板，后者在聊天里给 3 个回复。原云端插件身份和账号不会随源码复制。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
