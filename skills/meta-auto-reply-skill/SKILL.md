---
name: meta自动发布
description: Operate or update Varla Meta customer-service, KOL-reply, and Facebook content-scheduling rules for Meta Inbox, Webhooks, local product knowledge, and the verified Page API workflow. Use for DM auto-replies, human handoff, KOL collaboration screening, pre-sales, order, after-sales, comment moderation, Facebook video scheduling, and safe reply-policy changes.
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


# Varla Meta Customer Service

Use this skill for the Varla Meta reply service. It covers policy and knowledge routing; it does not authorize a live send, a permission change, or a production deployment by itself.

## Confirm the execution context

Before modifying a running service, identify whether the request targets Meta Inbox, a Webhook backend, or the local KOL reply assistant. The local `varla-kol-reply-assistant` drafts for manual copy/insert and must remain non-sending. Do not silently convert that assistant into an auto-send tool.

For API automation, use the active authorized Instagram account, validate Webhook signatures, ignore `is_echo`/`is_self`, and deduplicate with the Meta message ID. Only act inside Meta's permitted customer-initiated reply window; do not substitute a locally invented two-month window for API policy.

## Content publishing and scheduling

The current Varla publishing policy is **Facebook API auto-publishing only**. Instagram publishing remains manual unless the user explicitly changes this policy in the current request.

- Do not create, prepare, or run an Instagram container or Windows Instagram publish task for a normal content-scheduling request.
- Use the verified Facebook Page access token for Page `221101509307965` and the Graph API `v26.0` video upload flow with `published=false`, `unpublished_content_type=SCHEDULED`, and an absolute Unix `scheduled_publish_time`.
- Treat upload success or a returned video ID as an intermediate state. Poll `GET /{video_id}?fields=id,description,scheduled_publish_time,published,status` until processing is complete.
- Only report a successful schedule when `status.publishing_phase.publish_status == "scheduled"`, `status.video_status == "ready"`, and `published == false`. A `processing` or `not_started` state is not success.
- Re-read the description after upload. If an emoji or non-ASCII character becomes a replacement character, update the Facebook video description through the API using a UTF-8-safe source representation, then verify it again.
- Convert the user's stated timezone explicitly before scheduling. For New York dates in daylight-saving time, record both the local time and the UTC time in the audit file.
- Never print, save, or echo access tokens. Acquire a fresh Page token through the logged-in Meta Graph Explorer when needed, verify that the selected account is `Varla Scooter` and Page ID `221101509307965`, then pass the token through stdin or an in-memory process value.
- Write one audit JSON per scheduled post containing the source video path, caption, timezone/local time, UTC time, Facebook video ID, `video_status`, and `publish_status`. Record Instagram as `manual_only` and `auto_publish: false`.

The existing `tools/meta_dual_schedule.py` contains legacy Instagram-container helpers. For Facebook-only work, call `schedule_facebook_video()` and `verify_facebook_schedule()` directly; do not call the legacy `prepare()` path because it creates an Instagram container.

## Conversation control

- One eligible inbound message may produce at most one outgoing message. Never send multiple bubbles, repeated acknowledgements, or follow-ups without a new relevant inbound message.
- When Meta Inbox sends a human-authored message, suspend API replies for that conversation for 15 minutes. Extend the pause only if another human message is sent.
- Ignore low-information acknowledgements such as `ok`, `thanks`, `yes`, `no`, emoji-only messages, or a lone `?` when there is no actionable request.
- Do reply to a short but clear intent, including cooperation, sponsorship, KOL, price, shipping, order, warranty, repair, or product questions.
- For a long message whose exact detail cannot yet be resolved, send one concise acknowledgement that the appropriate team will review it; do not invent facts or make a commitment.
- If the topic is neither recognized nor safely resolvable from the approved knowledge base, remain silent rather than guessing.

## Routing policy

Read [references/routing-and-language.md](references/routing-and-language.md) before changing templates or deterministic classifiers.

| Intent | Reply route |
| --- | --- |
| M5S/M7S features, price, stock, availability, discount, normal purchase question | Use current approved product knowledge; if unavailable or time-sensitive, refer to `support@varlascooter.com` or the official Bio link. |
| Order, shipping, tracking, address, payment, delivery issue | Do not invent a date or tracking number. Refer to `support@varlascooter.com`. |
| Warranty, repair, battery/brake issue, refund, technical failure | Refer to `customer@varlascooter.com`; request concise evidence only when the approved template requires it. |
| KOL/cooperation, sponsorship, affiliate | Apply the follower and quality screen below. |
| Dealer, service partner, wholesale | Keep as manual review unless an approved partner template applies. |

## KOL cooperation screen

- Do not promise a free vehicle, payment, commission, or approval.
- If a creator has 8,000+ followers or strong demonstrated reach, ask for their social links, follower count, average views, audience countries, engagement data, and recent relevant content. The team reviews before confirmation.
- If they are below 8,000 followers or lack evidence of performance, politely decline the free-product request and offer the closed-beta/community route: use the community entry in the Bio/Linktree and ask the admin about available test pricing. Do not invent a price or availability.
- If a creator asks a short direct question about collaboration, it is actionable; do not discard it just because it is short.

## Product and customer support knowledge

- Retrieve approved local knowledge before stating M5S/M7S specifications, prices, shipping, warranty, discount codes, or campaign terms.
- Current product, inventory, price, shipping, and discount details are time-sensitive. If the knowledge source is absent, stale, contradictory, or incomplete, direct the user to the applicable mailbox instead of improvising.
- Use friendly, concise English for external DM replies. Keep one message self-contained and suitable for a customer-facing inbox.
- Do not state a delivery date. For approved shipping language, say collaboration orders and regular purchases are usually arranged within 1–3 days after confirmation/purchase and tracking is shared once available; avoid older launch/pre-order wording.

## Comment moderation

When the user asks to maintain the current brand-protection list, include exact lowercase keyword checks for `copy`, `clone`, `yozma`, `holy`, and `temu`, while preserving platform-specific moderation configuration. Do not assume a Meta setting applied to Instagram also covers Facebook: verify and configure each surface separately.

## Change and verification

1. Locate the active runtime and relevant template/rule file before editing.
2. Make the narrowest update that expresses the requested policy.
3. Test deterministic cases: human-pause, acknowledgement-ignore, clear cooperation inquiry, under-8k free-product request, 8k-plus data request, presales fallback, after-sales fallback, and duplicate-event suppression.
4. Verify through a controlled test conversation before describing the service as enabled.
5. Report the updated rule, the active runtime, and any Meta permission/window limitation.
