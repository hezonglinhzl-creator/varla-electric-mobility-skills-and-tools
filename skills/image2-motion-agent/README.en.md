# Image Motion and Dreamina Video Assistant / 广告图动效与即梦视频助手

[简体中文](README.md) | **English**

Analyze product/ad images while preserving text, logos and shape; preview prompts and commands before authorized video generation.

## Features

- English prompts with Chinese review
- Logo sweeps, text entrances and product motion
- A non-credit-consuming dry run

## What is included

| Part | Location |
| --- | --- |
| Dreamina Image-to-Video Command Wrapper | [dreamina-image2video](../../apps/dreamina-image2video/README.en.md) |
| Skill instructions | [SKILL.md](./SKILL.md) |

## 1. Set up the program first

### Dreamina Image-to-Video Command Wrapper (`dreamina-image2video`)

Python and your own Dreamina CLI/login; command previews do not require generation.

Open `../../apps/dreamina-image2video` first. Build CLI commands from JSON jobs, default to dry-run and execute only with --execute.

1. Install image2-motion-agent. The wrapper is `image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py`.
2. Create your job.json with image, prompt, duration, poll and video_resolution.
3. First run `python image2-motion-agent-program-package/image2-motion-agent/scripts/dreamina_image2video.py --job C:/path/job.json`.
4. Check `will_consume_credits: false` and review the prompts.
5. Before real generation, inspect `dreamina -h` for your installed version and log in. Add `--execute` only after explicit approval of the same job.

[Full program / browser-extension guide](../../apps/dreamina-image2video/README.en.md)

You manage the third-party CLI version and credits; no account or free credits are provided.

## 3. First task

| Prepare | Details |
| --- | --- |
| Input | One image, requested motion, duration and aspect ratio. |
| Output | Image analysis, bilingual prompts, a JSON job file and generation command. |

```text
Use image2-motion-agent to add a text entrance and logo sweep while preserving all text and the bike shape. Show prompts and a dry run first.
```


## Limits and troubleshooting

A dry run does not render video. Execution needs your Dreamina CLI, login and credits plus explicit --execute.

| Problem | Next step |
| --- | --- |
| Skill not visible | Check the installer output and destination SKILL.md, reopen Codex and start a new chat. |
| Program fails to start | Open its directory in PowerShell and run the documented command so the error remains visible; check that program's README. |
| Browser panel missing | Select the exact folder containing manifest.json, check supported websites and refresh the website tab. |
| External service unavailable | Supply your own authorization/settings and verify access. Keep local output rather than claiming a sync/send succeeded. |

## Privacy and status

This is a source/skill distribution. No real accounts, OAuth tokens, customer/KOL lists, contracts, orders, mailbox exports or business media are included. You configure your own services. Documentation and package paths were checked; live orders, sends and publications were not executed as part of documentation validation.
