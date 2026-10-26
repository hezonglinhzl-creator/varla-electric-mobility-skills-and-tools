# 飞书 Codex 本地 Skill

这个 skill 整合两条已经验证可用的本地链路。

## 1. 飞书聊天使用 Codex

```text
飞书消息 -> cc-connect -> 本地 Codex CLI
```

使用文件：

- `安装.bat`
- `配置.bat`
- `启动.bat`
- `检查状态.bat`

## 2. 自动修改飞书资料

```text
Codex -> Python 脚本 -> 飞书 OpenAPI -> 文档/多维表格
```

使用文件：

- `配置OpenAPI.bat`
- `检查OpenAPI.bat`
- `scripts\feishu_docs.py`
- `scripts\feishu_import_markdown_tables.py`
- `scripts\verify_native_tables.py`

OpenAPI 凭证保存在：

```text
%USERPROFILE%\.feishu-docs\config.json
```

skill 和 ZIP 中不包含真实 `app_secret`。

## 能做什么

- 在飞书聊天中调用本地 Codex
- 创建、读取和更新飞书文档
- 导入带飞书原生表格的 Markdown
- 写入多维表格记录
- 上传和替换合同附件
- 按邮箱更新 KOL code 等字段

## 不需要

不依赖 `lark-cli`。`cc-connect` 负责聊天桥接，Python OpenAPI 工具负责飞书资料操作。
