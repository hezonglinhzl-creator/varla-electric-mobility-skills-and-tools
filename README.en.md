# Varla Electric Mobility Toolkit / 电摩社媒与 KOL 工具箱

[简体中文](README.md) | **English**

Local programs, browser extensions and Codex skills for electric-mobility content production, creator operations and social reporting. Choose a program first, then use its paired skill; each complete-project ZIP includes both.

[Complete project downloads](独立下载清单.md) · [Published repositories](独立仓库清单.md) · [Browser-extension guide](docs/browser-extensions.en.md) · [Original local reply plugin](plugins/varla-kol-reply/README.en.md)

## Choose your task

| I want to… | Start here |
| --- | --- |
| Record creators and video metrics | KOL Collector / KOL Video Monitoring |
| Draft creator replies | KOL Reply Assistant; Chrome panel or local three-option plugin |
| Read mail and review tasks | Gmail Automation / KOL Command Center |
| Prepare an order or contract | Shopify KOL Order Tool / Contract Updater |
| Plan or break down videos | UGC Story Director / Video Storyboard Tool |
| Build social reports | Weekly Report / Social Insights Review |

## Before downloading

| Component | What to prepare |
| --- | --- |
| Windows programs | Windows, the program-specific Python/Node requirements and a folder you may write to |
| Browser extensions | Chrome or Edge; extension folder containing manifest.json |
| Codex workflows | A signed-in Codex client; local skill installation |
| External integrations | Your own Gmail/Feishu/Shopify/AdsPower/Dreamina access, only for the tools that use them |

## First use, step by step

1. Open the complete-project download catalog, find the program/task, and download **one complete ZIP** from its row. A ZIP is a compressed file already stored in this repository's packages directory; it does not require a separate GitHub repository.
2. Right-click the ZIP and choose Extract All. Keep the complete directory, not just a .bat or one program file.
3. Open `apps/<program>/README.en.md`. Follow its environment/setup steps and start the program. Some entries are prompt/template workflows with no separate app.
4. Return to the bundle root, run `安装Skill.cmd` and reopen Codex. Existing same-name skills are skipped.
5. Copy that project's first-task example from its README and supply your own files/links. Start with a short test input and inspect the expected result before business use.

## Included browser extensions and earlier plugin

[The extension guide](docs/browser-extensions.en.md) lists the exact folders, supported sites, required local ports, installation steps and first-use checks for KOL Recorder, Unified Collector, KOL Reply and Viral Video Collector. A browser extension must be loaded from the folder containing manifest.json.

The earlier **Varla KOL Reply** local plugin is included under plugins/varla-kol-reply with a repository marketplace and installation instructions. It gives three short reply options in Codex; the Chrome reply panel gives six. Cloud-account identity and login state are not transferred.

## Program directory

| Program / tool | What it does | Guide |
| --- | --- | --- |
| KOL 记录器 Chrome 插件 / KOL Recorder Chrome Extension | Read visible Instagram/TikTok creator fields and write a local Excel tracker. | [README](apps/kol-recorder-extension/README.en.md) |
| KOL 与爆款视频完整采集器 / KOL and Viral Video Collector Kit | Start the KOL recorder and video center together with the floating Varla browser panel. | [README](apps/varla-kol-collector/README.en.md) |
| Varla 统一采集 Chrome 插件 / Varla Unified Collector Extension | Switch between KOL records and video collection in one panel. | [README](apps/unified-collector-extension/README.en.md) |
| Instagram 当前指标监控核心 / Instagram Current Metrics Core | Maintain current metrics and discovery/check timestamps by shortcode, then aggregate creators. | [README](apps/varla-instagram-monitor/README.en.md) |
| KOL 网页回复 Chrome 插件 / KOL Browser Reply Extension | A floating KOL panel, message reading, six grouped replies, manual copy and a ChatGPT prompt. | [README](apps/varla-kol-reply-program/README.en.md) |
| KOL 邮件总控台程序 / KOL Command Center App | A local WebUI, four mail groups, knowledge retrieval, reply review, confirmation and pause. | [README](apps/varla-kol-command-center/README.en.md) |
| Shopify KOL 订单浏览器工具 / Shopify KOL Browser Order Tool | Single-order Excel validation, address checks, fill and a separate submit step. | [README](apps/shopify-order-bot/README.en.md) |
| 本地视频拆镜头与分镜表 / Local Shot Detection and Storyboards | Upload videos, split shots, extract frames, edit storyboards and export tables. | [README](apps/video-storyboard-tool/README.en.md) |
| 本地短视频评分分析 / Local Short Video Score Analyzer | Opening-hook checks, pacing, frames, waveforms and heuristic score exports. | [README](apps/video-score-analyzer/README.en.md) |
| 电摩爆款视频采集中心 / eMoto Viral Video Collection Center | Public-link collection, a local video list and exports with a Chrome capture extension. | [README](apps/viral-video-finder-extension/README.en.md) |
| 社媒排期与模拟发布原型 / Social Scheduling and Mock Publishing Prototype | A local dashboard, task validation, BullMQ worker and mock adapter. | [README](apps/varla-social-publisher/README.en.md) |
| 飞书本地 OpenAPI 工具包 / Local Feishu OpenAPI Toolkit | Documents, native tables, Base records and attachments, with setup/check scripts. | [README](apps/feishu-codex-local/README.en.md) |
| 即梦图生视频命令包装器 / Dreamina Image-to-Video Command Wrapper | Build CLI commands from JSON jobs, default to dry-run and execute only with --execute. | [README](apps/dreamina-image2video/README.en.md) |
| 电摩 AI 内容资料与验证工具 / eMoto AI Content Resources and Validation | Story-director and product-video resources with prompt-structure validation. | [README](apps/electric-moto-ai-workflow/README.en.md) |
| 社媒周报模板资料 / Social Reporting Templates | Platform aggregation, date checks and weekly/monthly reporting instructions. | [README](apps/varla-weekly-report/README.en.md) |

## What is ready, and what needs setup

- Programs are source distributions; Python/Node packages and external accounts are configured on your computer.
- Instagram monitoring currently processes collected input files; a successful run alone does not prove a live crawl.
- Social Publisher is a **mock-publishing prototype**. Real Meta/TikTok adapters are not configured.
- Orders, mail sends, affiliation changes and Feishu writes need the permissions and review specified by each project. Documentation validation did not execute these business actions.

## Common problems

| Problem | Resolution |
| --- | --- |
| Download/ZIP is confusing | Use the row's complete-package ZIP; extract everything before running a file. |
| Extension missing | Enable developer mode, load the exact manifest.json folder, then refresh the supported website. |
| Backend offline | Start the appropriate Python service and keep its window open; check its documented port. |
| KOL workbook missing | Run create_blank_workbook.py in KOL_recorder (or the recorder folder); it never overwrites an existing workbook. |
| Same port already used | Avoid running the KOL recorder and video-score tool together on 8765. |
| Module/command missing | Install the dependency from that program's README using the same runtime that starts it. |

## Privacy

Public packages contain instructions, source, safe templates and required public runtime assets. Real credentials, logged-in browser profiles, creator/customer records, orders, contracts, mail exports and business media are excluded. Use your own data/configuration and keep them local. Internal resource IDs/invite links in current distribution files were replaced with placeholders.

## Documentation reference

The guide layout follows the feature/environment/install/usage/FAQ structure in [GitHub Hans](https://github.com/52cik/github-hans). That browser translation tool is a reference, not a bundled Varla component.

[2026-10-28 package review and fixes](docs/release-notes-2026-10-28.md)
