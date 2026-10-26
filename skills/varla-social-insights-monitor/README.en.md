# Varla Social Insights Review / Varla 社媒洞察核对

[简体中文](README.md) | **English**

Review metrics on authorized Meta surfaces, record retrieval dates/missing values and prepare exact-URL Feishu updates.

## Features

- Visible backend-metric review
- Exact post URL matching
- Scoped Feishu update checks

## What is included

| Part | Location |
| --- | --- |
| Skill instructions | [SKILL.md](./SKILL.md) |

This project is a Codex skill/workflow with its own instructions or scripts; it has no separate app server to launch.

## 1. Set up the program first

No app installation is required. Prepare Codex and the input listed below. If the skill includes Python scripts, install the stated script dependency before running them.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Authorized Meta data, post links and the specified target table. |
| Output | A metric review with sources and retrieval dates. |

```text
Use varla-social-insights-monitor to check my Meta screenshots against post links and create a comparison table; mark missing metrics unavailable.
```


## Limits and troubleshooting

This is a workflow skill, without bundled Meta authorization, crawler, Feishu credentials or data.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
