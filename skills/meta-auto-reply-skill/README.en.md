# Meta Reply and Social Publishing Workflow / Meta 客服回复与社媒发布流程

[简体中文](README.md) | **English**

Maintain Meta support/KOL reply rules with source for the local social-publishing prototype.

## Features

- Support, after-sales and KOL routing
- Human handoff and reply drafts
- Local scheduling and a mock publishing prototype

## What is included

| Part | Location |
| --- | --- |
| Social Scheduling and Mock Publishing Prototype | [varla-social-publisher](../../apps/varla-social-publisher/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### Social Scheduling and Mock Publishing Prototype (`varla-social-publisher`)

Node.js 22, npm and Redis; Docker may provide Redis/MinIO, with FFmpeg for media.

Open `../../apps/varla-social-publisher` first. A local dashboard, task validation, BullMQ worker and mock adapter.

1. Install system Node.js 22+ and run npm install in this program folder.
2. Run START_VARLA.bat for the static dashboard, or powershell -File tools/start_varla.ps1 -CheckOnly for a non-starting diagnostic.
3. Redis and the worker do not start automatically. To develop the mock worker, supply your Redis and explicitly configure RUN_WORKER, MOCK_PUBLISHING and REDIS_URL.
4. The page has no upload/review/scheduling workflow. /api/health is a fixed 503 placeholder, not a real dependency check.

Local URL: `http://127.0.0.1:3000`

[Full program / browser-extension guide](../../apps/varla-social-publisher/README.en.md)

The launcher starts only the dashboard with system Node.js 22+ and never starts a worker automatically. Install npm dependencies first; inspect readiness with `powershell -File tools/start_varla.ps1 -CheckOnly`. Real adapters, OAuth, app review and an upload/scheduling workflow remain unimplemented.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | Messages, current product knowledge, platform and approved reply rules. |
| Output | Replies for review, routing suggestions or local mock-publishing jobs. |

```text
Use meta-auto-reply-skill to classify this message and draft a reply for review without sending or scheduling a real publication.
```


## Limits and troubleshooting

The bundled publisher has no configured real-platform adapter. A working UI or mock job does not mean a post was published.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
