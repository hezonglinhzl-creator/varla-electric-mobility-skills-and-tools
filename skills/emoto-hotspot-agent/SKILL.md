---
name: emoto-hotspot-agent
description: Find daily internet trends for electric dirt bike, e-moto, and off-road e-bike brand accounts, then judge whether each trend fits US TikTok, Instagram, or Shorts content before proposing safe, shootable video directions. Use when the user wants trend scanning, topic filtering, content-angle judging, or a daily hotspot report for an electric off-road motorcycle brand.
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


# eMoto Hotspot Agent

This skill helps Codex act like a daily content-ops scout for an electric dirt bike brand. It does not jump straight into copywriting. It first scans live internet trends, then filters for brand fit, then outputs safe and shootable video directions for US short-form platforms.

## When To Use

Use this skill when the user wants any of the following for an electric dirt bike, e-moto, or off-road e-bike brand:

- Daily trend scanning
- TikTok, Instagram Reels, or YouTube Shorts topic selection
- "What should we film today?" recommendations
- Hotspot judging before scriptwriting
- Competitor and category account monitoring
- A simple operations-ready report that separates do now, watch, adapt, skip, and risk

Do not use this skill when the task is only:

- Writing ad copy without trend research
- Creating dangerous stunt concepts
- Making exaggerated claims about speed, range, or safety
- Repackaging unrelated viral trends with no natural e-moto angle

## Core Rule

Always follow this order:

1. Find trends
2. Verify video frames
3. Judge fit
4. Propose video angles
5. Write light execution copy only after the angle is approved

Never start by drafting a script just because a trend looks popular.
Never promote a candidate into the report from title, hashtags, account name, or metrics alone.

## Source Priority

Scan live sources in this order unless the user narrows the scope:

1. TikTok trending videos, trending sounds, comment sections, and POV/opening-line patterns
2. Instagram Reels in outdoor, garage, dad gift, summer, modification, and youth-interest niches
3. YouTube Shorts for repeated hooks, titles, and format structure
4. Google Trends for US seasonal intent and event timing
5. Reddit for discussion pressure, objections, memes, anxieties, and gift angles
6. Competitor e-bike, electric dirt bike, and e-moto brand accounts
7. Adjacent niches:
   outdoor
   off-road
   garage
   dad gift
   summer fun
   bike check
   modifications
   teen gift
   first ride
   range anxiety

If local helper tools already exist in the workspace, they can be used as supplemental candidate collectors, but they do not replace live verification.

In this workspace, check [source-scan-queries.md](./references/source-scan-queries.md) for reusable query patterns and the local helper notes.

## Hotspot Types To Watch

Prioritize trends that map cleanly into short-form video behavior:

- Hot BGM or recurring sound
- Meme formats
- POV sentence patterns
- High-retention opening lines
- Comment-section debates
- Seasonal or calendar moments
- Outdoor riding energy
- Garage surprise setups
- Gift moments
- Toy/fun framing
- Speed-feel without unsafe behavior
- Range-anxiety or battery-convenience discussion

## Judging Workflow

For each candidate hotspot, first verify the visual frames. A candidate cannot enter `do-now`, `adapt`, or the top recommendations unless the frames confirm the content type.

Required frame checks:

- Main subject: bike, rider, product, garage build, wash process, jump, wheelie, or real riding scene
- Wrong-subject rejection: animal, unrelated person, generic lifestyle, ad-only product card, or beauty/celebrity bait as the main subject
- Action type: POV ride, wheelie, jump, clean build, wash transformation, garage reveal, gift reveal, or static product detail
- Frame evidence: note what is visible in at least 2 to 3 moments, such as opening frame, middle action frame, and final frame

If frames are unavailable, label the candidate `unverified` and keep it out of the final report.

After frame verification, answer all six questions before deciding:

1. Is it actually hot right now?
2. Is it relevant to US viewers?
3. Can it connect naturally to an electric dirt bike?
4. Can the current team shoot it with existing assets?
5. Does it create safety, policy, or controversy risk?
6. Is it best for TikTok, Instagram, YouTube Shorts, or KOL/creator execution?

Use the detailed scoring and decision rules in [judging-rubric.md](./references/judging-rubric.md).
Use [visual-verification.md](./references/visual-verification.md) before writing any report recommendation.

## Decision Labels

Every candidate must end in exactly one of these buckets:

- `do-now`: strong fit, safe enough, and shootable today
- `watch`: interesting but not yet strong enough or still forming
- `adapt`: useful structure or format, but needs an e-moto angle shift
- `skip`: weak fit, forced fit, or too expensive to produce
- `risk`: danger, policy, legality, brand-safety, or controversy concern

When the user wants Chinese output, map these labels back to plain-language equivalents:

- `do-now`: ready to shoot today
- `watch`: save and monitor
- `adapt`: change angle before using
- `skip`: not a fit
- `risk`: unsafe or policy-sensitive

Do not collapse `skip` and `risk` into one group. A bad fit and a risky fit are different decisions.

## Safety Guardrails

The account is aimed at US TikTok and Instagram users. Keep all output inside these boundaries:

- Do not encourage illegal road riding
- Do not present unsafe stunt riding as casual behavior
- Do not frame minors in high-speed or dangerous riding scenarios
- Do not exaggerate speed, range, durability, or safety
- Do not imply professional riding should be copied without context
- Prefer legal off-road areas, private land, supervised setups, slow-speed handling demos, garage content, surprise reveals, and gift reactions

If a trend is hot because it is reckless, criminal, deceptive, or obviously likely to trigger moderation, mark it `risk` even if it would perform well.

## Execution Standard

When the user asks for a daily report, produce:

- Up to 3 top recommended hotspots, only if frame-verified
- 3 to 5 watchlist hotspots
- A short "do not chase" list with reasons
- 3 to 5 video topics that can be shot today

If there is only 1 real frame-verified hotspot, say there is only 1. Do not fill the top 3 with weak or unverified candidates.

Use the report shape in [report-template.md](./references/report-template.md).

The top 3 hotspots must include:

- Hotspot name
- Source platform
- Frame verification
- Why it is hot
- Why it fits or does not fit e-moto
- Recommended video direction
- 3-second hook
- Rough structure
- Needed assets
- TikTok caption
- Instagram caption
- Cover text
- Comment prompt
- Risk note
- Priority `P0` / `P1` / `P2` / `P3`

## Recommended Operating Loop

For a normal daily run:

1. Confirm target market is US unless the user says otherwise.
2. Search live sources and capture 10 to 20 candidate trends.
3. Open each serious candidate and inspect frames or screenshots.
4. Remove anything where the visual subject does not match the claimed angle.
5. Remove anything clearly unrelated, stale, or unsafe.
6. Score the remaining candidates with the rubric.
7. Sort by visual match and natural e-moto fit first, not raw virality alone.
8. Promote only frame-verified candidates into fully developed recommendations.
9. Put borderline items into `watch` or `adapt`.
10. End with 3 to 5 "today we can film this" topics for the ops team.

## Output Style

Write for a content operator who wants to know what to shoot today at a glance.

- Be direct
- Prefer short headings and compact reasoning
- Explain why something should be skipped
- Mention exact safety or policy concerns when relevant
- Keep hooks and captions usable, not overly polished
- Avoid overclaiming trend certainty when evidence is thin

## If Browsing Is Limited

If live platform access is blocked, say so clearly and fall back in this order:

1. Google Trends
2. Reddit
3. Recent search results from web search
4. Existing local research files in the workspace

In fallback mode, label any freshness limitation explicitly and avoid saying a trend is confirmed-hot unless it was verified from a live or recent source.
