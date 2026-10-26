# 飞书文档与本地 Codex 工具 / Feishu Documents and Local Codex Tools

**简体中文** | [English](README.en.md)

通过本地 Python OpenAPI 工具读取、创建和更新飞书文档、多维表格及附件。

## 功能特性

- 文档和原生表格导入
- 多维表格记录操作
- 本地凭据配置与状态检查

## 这个包里有什么

| 内容 | 位置 |
| --- | --- |
| 飞书本地 OpenAPI 工具包 | [feishu-codex-local](../../apps/feishu-codex-local/README.md) |
| Skill 指令 | [SKILL.md](./SKILL.md) |

## 1. 先准备程序

### 飞书本地 OpenAPI 工具包 (`feishu-codex-local`)

Windows、Python、自己的飞书应用权限；聊天桥接可选。

先进入 `../../apps/feishu-codex-local`。文档、原生表格、Base 和附件操作，带配置与检查脚本。

1. 先打开 `配置OpenAPI.bat`，按提示填写自己的 App ID 和 App Secret。
2. 配置保存在 `%USERPROFILE%\.feishu-docs\config.json`，只留在自己电脑。
3. 运行 `检查OpenAPI.bat`，如果权限不足，到自己的飞书开发者后台补权限并发布应用版本。
4. 在本目录运行 `python scripts/feishu_docs.py --help` 查看当前支持命令，或让已安装 Skill 的 Codex先只读指定文档。
5. 要从飞书聊天调用 Codex，才另行使用安装/配置/启动桥接入口，并准备 cc-connect；OpenAPI 资料操作可单独使用。

[查看完整程序与浏览器插件安装说明](../../apps/feishu-codex-local/README.md)

不能访问未授权资源；配置文件不要上传 GitHub，也不要把失败检查当同步成功。

## 3. 第一次怎么用

| 准备项 | 内容 |
| --- | --- |
| 输入 | 你自己的飞书应用凭据、有访问权的文档或 Base 链接、待写入内容。 |
| 输出 | 飞书结果链接、更新记录和读取核验结果。 |

```text
使用 feishu-codex-local，先检查配置，再只读我给的 Base 链接，列出字段和前 3 条记录，不做写入。
```


## 当前限制与常见问题

公开包没有飞书账号或 app_secret；聊天机器人桥接是可选功能，需另外安装和配置 cc-connect。

| 问题 | 怎么处理 |
| --- | --- |
| 找不到 Skill | 检查安装窗口结果和目标 SKILL.md，重新打开 Codex 并新建对话。 |
| 程序启动失败 | 在程序目录打开 PowerShell 运行本文命令，让错误保留在窗口，再对照对应程序 README。 |
| 网页看不到插件 | 确认选中直接包含 manifest.json 的目录、网站受支持，并刷新网页。 |
| 外部服务不可用 | 配置自己的授权并检查资源权限；保留本地结果，不把失败说成同步/发送成功。 |

## 隐私与验证范围

这是程序源码与 Skill 分发包，不附带真实账号、OAuth 令牌、客户/KOL 台账、合同、订单、邮箱导出或业务媒体。服务需使用自己的配置。已检查文档和包内入口；此次文档核对没有执行真实下单、发邮件或发布内容。
