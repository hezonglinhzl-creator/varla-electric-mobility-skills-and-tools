# Varla Social Weekly and Monthly Reports / Varla 社媒周报与月报

[简体中文](README.md) | **English**

Reconcile supplied social screenshots/CSV by date and platform to produce weekly comparisons, monthly reports and Feishu-ready tables.

## Features

- Date-boundary and availability checks
- Platform-level owned/KOL aggregation
- Metric-basis notes and paste-ready tables

## What is included

| Part | Location |
| --- | --- |
| Social Reporting Templates | [varla-weekly-report](../../apps/varla-weekly-report/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### Social Reporting Templates (`varla-weekly-report`)

Codex and your own screenshots/CSV.

Open `../../apps/varla-weekly-report` first. Platform aggregation, date checks and weekly/monthly reporting instructions.

1. This directory contains templates/skill resources, with no server to start.
2. Run `安装Skill.cmd` at the full bundle root and reopen Codex.
3. Provide your date ranges, screenshots and CSV and invoke 周报skill with the required platform scope.
4. Review dates, metric definitions and missing data before using the tables.

[Full program / browser-extension guide](../../apps/varla-weekly-report/README.en.md)

No business screenshots/data or automatic dashboard login are included.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Your screenshots, CSV and current/comparison date ranges. |
| Output | A report, metric tables and missing-data notes. |

```text
Use 周报skill with only my supplied Instagram data, compare these two periods, label missing dates and produce a Feishu-ready table.
```


## Limits and troubleshooting

varla-weekly-report is a template/skill bundle without a standalone web app. Business screenshots, CSV and past reports are excluded.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
