---
name: feishu-codex-local
description: Use when connecting Feishu chat to a local Codex through cc-connect, or when reading, creating, importing, and updating Feishu documents, Base tables, records, and attachments through local Python OpenAPI tools.
---

## Portable distribution paths / 完整包程序位置

Before running a program, read `PACKAGE-LOCATION.json` beside this installed SKILL.md.
Its `apps` object maps each bundled program name to the real extracted directory;
`package_root` points to the complete bundle. Use those paths first. Absolute paths
in older examples below are historical examples, not automatic defaults.
If this file is missing or the bundle was moved, rerun the complete project's
install.ps1 to refresh the mapping. Keep the extracted program directory.
Never treat YOUR_* placeholders as configured credentials or resource IDs.

运行程序前先读取本 SKILL.md 旁边的 `PACKAGE-LOCATION.json`：`apps` 是实际程序目录，
`package_root` 是完整包位置。下文旧电脑绝对路径只作为历史示例，不能自动照用。
缺少映射或完整包搬家后，重新运行完整包 install.ps1；保留解压后的程序目录。
YOUR_* 占位符不代表已配置账号或资源；真实写入前必须使用自己的授权和目标链接。


# Feishu Codex Local

Keep the two local capabilities separate:

```text
Feishu chat -> cc-connect -> local Codex CLI
Feishu data -> local Python -> Feishu OpenAPI
```

`lark-cli` is not required.

## Route Requests

| User intent | Route |
|---|---|
| Use Codex from Feishu chat | cc-connect bridge |
| Read/write Feishu docs | `scripts/feishu_docs.py` |
| Import Markdown with native tables | `scripts/feishu_import_markdown_tables.py` |
| Verify native table blocks | `scripts/verify_native_tables.py` |
| Update Base records or attachments | import `feishu_docs.py` and call OpenAPI |

## CC-Connect Workflow

1. Inspect Node.js, cc-connect, Codex login, and `~/.cc-connect/config.toml`.
2. Run `scripts/install-windows.ps1` when cc-connect is missing.
3. Run `scripts/configure-bridge.ps1` when bridge config is missing.
4. Run `scripts/start-bridge.ps1`.
5. Verify `platform ready`, `engine started`, `cc-connect is running`, and WebSocket connected.
6. Ask the user to send `/restart`, then `测试，只回复 ok`.

Prefer the working Codex executable under `%LOCALAPPDATA%\OpenAI\Codex\bin`. A WindowsApps `Access is denied` error means the wrong executable was selected.

## OpenAPI Workflow

Credentials are stored locally at:

```text
%USERPROFILE%\.feishu-docs\config.json
```

Never print, return, or package `app_secret`.

Configure and check:

```powershell
python .\scripts\feishu_docs.py configure
python .\scripts\feishu_docs.py check
```

For document work, use the helper commands shown by `--help`. For Base, attachment, or unsupported endpoints, import the helper and reuse:

- `load_config()`
- `get_tenant_access_token()`
- `http_json()`

Parse `app_token`, `table_id`, `view_id`, document ID, and wiki token from each user-provided URL. Keep changing Feishu links as per-run input rather than hardcoding them.

## Safety

- Back up records or document blocks before replacement.
- Match people by normalized email before using handle or name.
- Do not overwrite existing fields unless the user explicitly requests replacement.
- Re-read changed records or blocks and verify exact values.
- Keep bridge credentials and OpenAPI credentials out of generated artifacts.
- Do not start a second cc-connect process for the same bot.
