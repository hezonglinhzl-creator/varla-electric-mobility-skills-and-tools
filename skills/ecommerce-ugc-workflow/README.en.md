# Electric Mobility UGC Workflow / 电摩真人 UGC 内容工作流

[简体中文](README.md) | **English**

Turn electric-mobility product references into realistic UGC stories, character assets, shot plans, video prompts and social copy.

## Features

- Reference-bound product appearance
- Two-part stories with explicit speakers
- TikTok / Instagram post copy

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
| Input | Product images, verified specifications, audience, duration and story brief. |
| Output | Character prompts, timed shots, English generation prompts and a Chinese review version. |

```text
Use ecommerce-ugc-workflow to plan two 10-second family-gift scenes using my product reference. Start with a storyboard and use only verified specifications.
```


## Limits and troubleshooting

This is a Codex authoring workflow, not a standalone video generator. Rendering requires your own image/video tool.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
