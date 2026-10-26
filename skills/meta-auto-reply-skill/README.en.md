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

1. Open PowerShell here, run `Copy-Item .env.example .env`, set your local secrets and keep `MOCK_PUBLISHING=true`.
2. Run `npm install`, then `npm run db:generate` and `npm run db:push`.
3. Start Redis, check REDIS_URL in `.env`, then run `npm run dev`.
4. In another terminal run `$env:RUN_WORKER='true'; $env:MOCK_PUBLISHING='true'; $env:REDIS_URL='redis://127.0.0.1:6379'; npm run worker`.
5. Open the dashboard for mock jobs only. Resolve database, Redis, storage and worker health failures first.

Local URL: `http://127.0.0.1:3000`

[Full program / browser-extension guide](../../apps/varla-social-publisher/README.en.md)

Source rejects unconfigured real adapters. Meta/TikTok publishing, OAuth, app review and public media URLs still need integration; mock success is not a live publication.

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
