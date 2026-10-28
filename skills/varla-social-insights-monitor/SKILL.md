---
name: varla-social-insights-monitor
description: Review Varla social post performance from authorized Meta surfaces, record retrieval dates, and prepare narrowly scoped Feishu updates after verifying post URLs and table fields.
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


# Varla Social Insights Monitor

Read [Meta and Feishu field notes](references/meta-and-feishu-field-notes.md) before collecting metrics. Use only data visible through an account the operator has access to. Label missing metrics as unavailable. Match Feishu records using the existing channel and publication date fields, verify the exact post URL, update only requested fields, and read back changes.

This skill is a workflow guide. Account access and data are configured locally.
