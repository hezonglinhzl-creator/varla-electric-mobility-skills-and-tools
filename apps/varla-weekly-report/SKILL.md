---
name: varla-weekly-report
description: Build Varla/Himiway weekly social media reports from local TikTok, Instagram, Facebook, and red influencer screenshots or pasted metrics. Use when the user asks to update Varla weekly data, generate a Feishu-native weekly report/table, calculate total interaction, compare this week with last week, or process files under C:/path/to/your-project
---

# Varla Weekly Report

## Output Contract

Return one Feishu-native Markdown table that can be pasted directly into an existing Feishu table. Do not split the output into multiple tables unless the user explicitly asks.

Use this exact schema and row order:

| 时间 | 平台 | 浏览/播放 | 点赞 | 评论 | 转发 | 总互动量 | 覆盖人数 | 访问数 | 关注数 | 内容互动/点赞评论分享 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 本周周期 | Ins |  |  |  |  |  |  |  |  |  |
| 本周周期 | Tk |  |  |  |  |  |  |  |  |  |
| 本周周期 | FB |  |  |  |  |  |  |  |  |  |
| 本周周期 | 红人 |  |  |  |  |  |  |  |  |  |
| 本周周期 | 总计 |  |  |  |  |  |  |  |  |  |
| 环比 | Ins |  |  |  |  |  |  |  |  |  |
| 环比 | Tk |  |  |  |  |  |  |  |  |  |
| 环比 | FB |  |  |  |  |  |  |  |  |  |
| 环比 | 红人 |  |  |  |  |  |  |  |  |  |
| 环比 | 总计 |  |  |  |  |  |  |  |  |  |

## Data Source Workflow

Use `C:/path/to/your-project` as the default local data folder when the user mentions Varla weekly data but does not give another path.

Look for week-named files first:

- Instagram: `ins\<week>.png`, `ins\<week>内容.png`, `ins\<week>具体.png`
- Facebook: `fb\<week>.png`, `fb\<week>内容.png`, `fb\<week>具体.png`
- TikTok: `tk\<week>.png`

Infer the current week from the user request or newest week-labeled screenshots. Infer the previous week from the immediately prior weekly rows, local files, or pasted table data. If a value is not present, leave the cell blank.

## Extraction Rules

Map platform metrics into the fixed columns:

- Instagram: use overview screenshots for `浏览/播放`, `覆盖人数`, `访问数`, `关注数`, and `内容互动/点赞评论分享`; use detailed screenshots for `点赞`, `评论`, and `转发`.
- TikTok: use Studio overview for `浏览/播放`, `点赞`, `评论`, `转发`, and `访问数`; set `内容互动/点赞评论分享` to `点赞 + 评论 + 转发` when the platform does not provide a separate content-interaction value.
- Facebook: use overview screenshots for `浏览/播放`, `覆盖人数`, `访问数`, `关注数`, and `内容互动/点赞评论分享`; use detailed screenshots for `点赞`, `评论`, and `转发`.
- 红人: only use values explicitly provided by local files, screenshots, or the user; otherwise leave cells blank.

Convert abbreviated values before calculating:

- `9.4万` -> `94,000`
- `46.0万` -> `460,000`
- `1.2M` -> `1,200,000`
- `5.3K` -> `5,300`

## Calculation Rules

Calculate `总互动量` horizontally for every platform row:

`总互动量 = 点赞 + 评论 + 转发`

For `总计`, sum numeric values in each column across `Ins`, `Tk`, `FB`, and `红人`. Treat blank cells as missing and do not force them to zero in the displayed table.

For `环比`, calculate:

`(本周数值 - 上周数值) / 上周数值`

Format as one decimal place with a sign, for example `+43.9%` or `-25.5%`. Leave the cell blank when the current value, previous value, or previous denominator is blank or zero. Use explicit `0` only when the source metric is truly zero.

## Style Rules

- Never write `未提供`, `N/A`, `Unknown`, or similar placeholders in the table.
- Keep missing cells blank.
- Do not wrap the table in a code block.
- Do not use HTML tables.
- Keep the final answer focused on the paste-ready table unless the user asks for analysis.
- When saving a local copy, use: `C:/path/to/your-project`.

## Final Check

Before answering, verify:

- There is exactly one table for the weekly report.
- The column order matches the contract.
- `总互动量` is filled wherever `点赞`, `评论`, and `转发` are available.
- All `环比` cells use the previous week as baseline.
- No cell contains `未提供` or filler text.
