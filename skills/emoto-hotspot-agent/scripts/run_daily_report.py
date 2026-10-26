#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"


@dataclass(frozen=True)
class TrendSeed:
    name: str
    query: str
    theme: str
    platform_hint: str


TREND_SEEDS: list[TrendSeed] = [
    TrendSeed("Father's Day garage reveal", "Father's Day gift bike", "fathers-day-gift", "TikTok"),
    TrendSeed("Garage surprise bike gift", "garage surprise gift bike", "garage-surprise", "TikTok"),
    TrendSeed("Summer ride POV", "summer ride POV electric bike", "summer-pov", "TikTok"),
    TrendSeed("Electric dirt bike POV", "electric dirt bike POV", "ride-pov", "TikTok"),
    TrendSeed("Bike wash transformation", "bike wash transformation", "bike-wash", "TikTok"),
    TrendSeed("Talaria custom/build talk", "talaria", "bike-check-build", "TikTok"),
    TrendSeed("Sur-Ron custom/build talk", "surron", "bike-check-build", "TikTok"),
]


RISK_PATTERNS = [
    r"\bcatch us\b",
    r"\bfeds\b",
    r"\boutlaws?\b",
    r"\bwheelie\b",
    r"\bbornforspeed\b",
    r"\b37 mph\b",
    r"\blast units\b",
    r"\bselling fast\b",
]

BIKE_TERMS = [
    "bike",
    "ebike",
    "e-bike",
    "electric bike",
    "dirt bike",
    "motorcycle",
    "emoto",
    "talaria",
    "surron",
    "stark",
    "moto",
]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.load(res)


def parse_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "").lower()
    word_match = re.search(r"([\d.]+)\s*(million|thousand|billion)", text)
    if word_match:
        number = float(word_match.group(1))
        scale = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}[word_match.group(2)]
        return int(number * scale)
    match = re.match(r"^([\d.]+)\s*([kmb])?$", text)
    if match:
        number = float(match.group(1))
        scale = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(match.group(2) or "", 1)
        return int(number * scale)
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def fmt_count(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M".replace(".00M", "M").replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return str(value)


def compact(text: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def tiktok_link(author: str, video_id: str) -> str:
    return f"https://www.tiktok.com/@{author}/video/{video_id}"


def parse_create_time(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def is_risky_text(text: str) -> bool:
    low = text.lower()
    return any(re.search(pattern, low) for pattern in RISK_PATTERNS)


def bike_relevance_score(text: str) -> int:
    low = text.lower()
    score = 0
    for term in BIKE_TERMS:
        if term in low:
            score += 1
    return score


def infer_theme_priority(theme: str) -> int:
    order = {
        "fathers-day-gift": 400,
        "garage-surprise": 390,
        "summer-pov": 380,
        "ride-pov": 360,
        "bike-wash": 350,
        "bike-check-build": 300,
    }
    return order.get(theme, 0)


def heat_bucket(views: int, likes: int) -> str:
    if views >= 1_000_000 or likes >= 100_000:
        return "very hot"
    if views >= 300_000 or likes >= 20_000:
        return "hot"
    if views >= 80_000 or likes >= 5_000:
        return "warm"
    return "early signal"


def classify_action(theme: str, title: str, views: int, likes: int) -> str:
    text = f"{theme} {title}".lower()
    relevance = bike_relevance_score(text)
    if is_risky_text(text):
        return "risk"
    if theme in {"fathers-day-gift", "garage-surprise"} and relevance == 0:
        return "skip"
    if theme in {"summer-pov", "ride-pov"} and relevance == 0:
        return "skip"
    if theme in {"fathers-day-gift", "garage-surprise", "summer-pov", "bike-wash"}:
        if views >= 80_000 or likes >= 5_000:
            return "do-now"
        return "watch"
    if theme == "ride-pov":
        if views >= 300_000 or likes >= 20_000:
            return "adapt"
        return "watch"
    if theme == "bike-check-build":
        if views >= 150_000 or likes >= 10_000:
            return "adapt"
        return "watch"
    return "skip"


def channel_for(theme: str) -> str:
    return {
        "fathers-day-gift": "TikTok + Instagram",
        "garage-surprise": "TikTok + KOL",
        "summer-pov": "TikTok + Instagram",
        "ride-pov": "TikTok",
        "bike-wash": "Instagram + YouTube Shorts",
        "bike-check-build": "TikTok + KOL",
    }.get(theme, "TikTok")


def risk_note_for(theme: str, text: str) -> str:
    low = text.lower()
    if is_risky_text(low):
        return "Avoid illegal-road, chase, wheelie, or speed-bait framing."
    if theme in {"ride-pov", "summer-pov"}:
        return "Keep it on legal private land or approved low-risk routes. Do not imply unsafe speed."
    if theme in {"fathers-day-gift", "garage-surprise"}:
        return "Keep riders adult or supervised. Do not frame minors in risky riding situations."
    return "Do not exaggerate speed, range, or safety."


def reason_for(theme: str, views: int, likes: int, title: str) -> str:
    metric = f"{fmt_count(views)} views / {fmt_count(likes)} likes"
    mapping = {
        "fathers-day-gift": f"Seasonal gifting demand is already live ahead of Father's Day, and surprise-bike reactions are driving emotional retention. Current signal: {metric}.",
        "garage-surprise": f"Garage reveal and surprise-reaction videos create instant emotional payoff and strong comment behavior. Current signal: {metric}.",
        "summer-pov": f"Summer break and sunset-cruise POV content is performing because it sells freedom, outdoor time, and low-friction fun. Current signal: {metric}.",
        "ride-pov": f"POV ride clips remain a durable short-form format because the viewer immediately understands the motion and sensation. Current signal: {metric}.",
        "bike-wash": f"Cleaning and transformation content keeps working because the before/after visual payoff lands without needing dialogue. Current signal: {metric}.",
        "bike-check-build": f"Custom-build and colorway talk works when viewers debate parts, style, and 'cleanest build' status. Current signal: {metric}.",
    }
    return mapping.get(theme, f"Fresh signal detected. Current signal: {metric}.")


def fit_for(theme: str) -> str:
    return {
        "fathers-day-gift": "It fits e-moto naturally as a dad-gift or family-garage reveal angle without forcing the trend.",
        "garage-surprise": "It fits because the bike itself is the payoff object, so the reveal can be centered on the garage, key-turn, and first reaction.",
        "summer-pov": "It fits because e-moto content already sells outdoor freedom and summer riding mood, as long as the route and speed framing stay safe.",
        "ride-pov": "It can fit, but raw POV often drifts into risky riding. The angle should be adapted toward feel, terrain, and legal environment.",
        "bike-wash": "It fits well because a muddy-to-clean electric dirt bike transformation is visually strong and easy to shoot with existing assets.",
        "bike-check-build": "It fits if the team shifts from outlaw energy to safe customization, parts talk, or garage build pride.",
    }.get(theme, "It has a possible e-moto angle.")


def direction_for(theme: str) -> str:
    return {
        "fathers-day-gift": "Shoot a Father's Day surprise reveal in the garage: cover, key-on, dad reaction, then a calm first look at the bike.",
        "garage-surprise": "Use a spouse/family reveal format where the bike is already staged in the garage and the reaction is the story.",
        "summer-pov": "Film a sunset or after-school summer cruise that sells outdoor fun without any speed-flex framing.",
        "ride-pov": "Adapt the POV trend into low-risk private-land riding, hill entry, terrain texture, and sound-design detail.",
        "bike-wash": "Shoot a muddy-bike cleaning transformation with foam, rinse, detail shots, and a final beauty pass.",
        "bike-check-build": "Turn build hype into a clean garage bike-check: parts close-ups, colorway, tires, suspension, and one safe roll-out shot.",
    }.get(theme, "Propose a simple product-first video angle.")


def hook_for(theme: str) -> str:
    return {
        "fathers-day-gift": "POV: Dad thinks we're just opening the garage...",
        "garage-surprise": "He had no idea the bike was already waiting inside.",
        "summer-pov": "POV: school is out and this is the summer plan.",
        "ride-pov": "POV: the trail sounds better on electric.",
        "bike-wash": "This muddy e-moto is about to look brand new.",
        "bike-check-build": "Cleanest garage setup or too much? Be honest.",
    }.get(theme, "Today's angle in one line.")


def structure_for(theme: str) -> str:
    return {
        "fathers-day-gift": "0-3s reveal setup -> 3-8s reaction -> 8-15s bike close-ups -> 15-22s calm first-roll shot -> 22-28s CTA.",
        "garage-surprise": "0-3s door opens -> 3-7s face reaction -> 7-14s details -> 14-22s key-on / cockpit -> 22-28s comment CTA.",
        "summer-pov": "0-3s hook -> 3-8s helmet or handlebar POV -> 8-15s summer-location cutaways -> 15-24s relaxed ride shots -> 24-30s CTA.",
        "ride-pov": "0-3s immediate handlebar angle -> 3-10s terrain texture -> 10-18s sound + suspension feel -> 18-25s rider reaction -> 25-30s CTA.",
        "bike-wash": "0-3s muddy hero shot -> 3-10s foam/rinse -> 10-18s detail cleaning -> 18-24s final reveal -> 24-30s comment CTA.",
        "bike-check-build": "0-3s full-bike flash -> 3-12s part callouts -> 12-20s cockpit/tires/suspension -> 20-28s safe roll shot -> 28-30s debate CTA.",
    }.get(theme, "Hook -> proof -> product payoff -> CTA.")


def assets_for(theme: str) -> str:
    return {
        "fathers-day-gift": "Garage, covered bike, one adult reaction subject, key-turn shot, product beauty shots.",
        "garage-surprise": "Garage, reveal setup, one family member, bike staged clean, good phone audio for reaction.",
        "summer-pov": "Helmet/handlebar POV, legal route or private land, sunset or after-school light, rider close-ups.",
        "ride-pov": "POV mount, low-risk terrain, rider gloves/controls, wheel and suspension detail shots.",
        "bike-wash": "Dirty bike, foam/water setup, brushes, microfiber, final clean spot for reveal.",
        "bike-check-build": "Clean garage, detailed bike, part close-ups, lighting for paint/tire/suspension shots.",
    }.get(theme, "Bike, rider, and a clean filming plan.")


def caption_tiktok(theme: str) -> str:
    return {
        "fathers-day-gift": "Would your dad see this coming? #FathersDay #emoto #electricdirtbike #garagefinds",
        "garage-surprise": "The garage reveal made this one. Would you pull this off? #emoto #surprisegift #dirtbike",
        "summer-pov": "This might be the best kind of summer plan. #emoto #summervibes #povride",
        "ride-pov": "Not speed. Just sound, grip, and trail feel. #emoto #pov #offroad",
        "bike-wash": "Mud off, details on. Satisfying enough? #emoto #bikewash #transformation",
        "bike-check-build": "Garage build check. What would you change first? #surron #talaria #emoto",
    }.get(theme, "#emoto")


def caption_instagram(theme: str) -> str:
    return {
        "fathers-day-gift": "A better Father's Day reveal than another tie. Clean garage setup, real reaction, zero hard sell.",
        "garage-surprise": "When the garage reveal does the storytelling for you. Product-first, reaction-led, and easy to execute.",
        "summer-pov": "Summer light, quiet power, and a route that feels like freedom. Keep it simple and shootable.",
        "ride-pov": "A POV angle works when the terrain and sound are the hero, not risky riding.",
        "bike-wash": "One of the easiest ways to make an e-moto post feel satisfying: muddy to clean in under 30 seconds.",
        "bike-check-build": "Build pride works. Keep it in the garage, keep it detailed, and let the audience debate the setup.",
    }.get(theme, "Electric dirt bike content angle.")


def cover_text(theme: str) -> str:
    return {
        "fathers-day-gift": "DAD DIDN'T EXPECT THIS",
        "garage-surprise": "GARAGE REVEAL",
        "summer-pov": "SUMMER RIDE PLAN",
        "ride-pov": "TRAIL FEEL > SPEED",
        "bike-wash": "MUDDY TO CLEAN",
        "bike-check-build": "CLEAN BUILD CHECK",
    }.get(theme, "TODAY'S ANGLE")


def comments_for(theme: str) -> str:
    return {
        "fathers-day-gift": "Would this work better as a dad gift or a birthday reveal?",
        "garage-surprise": "Better with a garage reveal or outdoor reveal?",
        "summer-pov": "Would you film this at sunset or golden hour trail-side?",
        "ride-pov": "More POV or more rider reaction next time?",
        "bike-wash": "More satisfying: foam stage or final reveal?",
        "bike-check-build": "What would you upgrade first on this setup?",
    }.get(theme, "What would you test next?")


def priority_for(theme: str, views: int, likes: int) -> str:
    if theme in {"fathers-day-gift", "garage-surprise"} and (views >= 100_000 or likes >= 5_000):
        return "P0"
    if theme in {"summer-pov", "bike-wash"} and (views >= 100_000 or likes >= 5_000):
        return "P1"
    if theme in {"ride-pov", "bike-check-build"}:
        return "P2"
    return "P3"


def fetch_tiktok_seed(seed: TrendSeed, count: int = 8) -> list[dict]:
    url = "https://www.tikwm.com/api/feed/search?" + urllib.parse.urlencode(
        {"keywords": seed.query, "count": str(count), "cursor": "0"}
    )
    payload = fetch_json(url)
    videos = ((payload.get("data") or {}).get("videos") or (payload.get("data") or {}).get("items") or [])[:count]
    rows: list[dict] = []
    for video in videos:
        author = (video.get("author") or {}).get("unique_id") or (video.get("author") or {}).get("uniqueId") or video.get("author_unique_id")
        video_id = video.get("video_id") or video.get("id") or video.get("aweme_id")
        if not author or not video_id:
            continue
        title = compact(video.get("title") or video.get("desc") or "", 180)
        views = parse_count(video.get("play_count") or video.get("playCount") or video.get("play"))
        likes = parse_count(video.get("digg_count") or video.get("diggCount") or video.get("likes"))
        created_at = parse_create_time(video.get("create_time"))
        rows.append(
            {
                "seed_name": seed.name,
                "query": seed.query,
                "theme": seed.theme,
                "platform": seed.platform_hint,
                "author": author,
                "video_id": str(video_id),
                "title": title,
                "views": views,
                "likes": likes,
                "link": tiktok_link(author, str(video_id)),
                "created_at": created_at.isoformat() if created_at else "",
            }
        )
    return rows


def is_recent_2026(row: dict, report_date: date, max_age_days: int = 45) -> bool:
    raw = row.get("created_at") or ""
    if not raw:
        return False
    try:
        created = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if created.year != 2026:
        return False
    cutoff = datetime.combine(report_date, datetime.min.time(), tzinfo=timezone.utc) - timedelta(days=max_age_days)
    ceiling = datetime.combine(report_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    return cutoff <= created < ceiling


def score_candidate(row: dict) -> int:
    base = infer_theme_priority(row["theme"])
    base += min(row["views"] // 5_000, 120)
    base += min(row["likes"] // 500, 80)
    base += min(row.get("relevance", 0) * 25, 100)
    if row["action"] == "do-now":
        base += 120
    elif row["action"] == "adapt":
        base += 80
    elif row["action"] == "watch":
        base += 40
    elif row["action"] == "risk":
        base -= 100
    return base


def annotate(rows: Iterable[dict]) -> list[dict]:
    annotated: list[dict] = []
    for row in rows:
        title = row["title"]
        action = classify_action(row["theme"], title, row["views"], row["likes"])
        text = f'{title} {row["author"]}'
        row = dict(row)
        row["relevance"] = bike_relevance_score(text)
        row["heat"] = heat_bucket(row["views"], row["likes"])
        row["action"] = action
        row["best_channel"] = channel_for(row["theme"])
        row["risk_note"] = risk_note_for(row["theme"], text)
        row["score"] = score_candidate(row)
        annotated.append(row)
    annotated.sort(key=lambda item: item["score"], reverse=True)
    return annotated


def unique_by_theme(rows: Iterable[dict], allowed_actions: set[str]) -> list[dict]:
    picked: list[dict] = []
    seen_themes: set[str] = set()
    for row in rows:
        if row["action"] not in allowed_actions:
            continue
        if row["theme"] in seen_themes:
            continue
        picked.append(row)
        seen_themes.add(row["theme"])
    return picked


def select_top_recommendations(rows: list[dict]) -> list[dict]:
    primary = unique_by_theme(rows, {"do-now"})
    if len(primary) >= 3:
        return primary[:3]
    used_themes = {row["theme"] for row in primary}
    for row in rows:
        if row["action"] not in {"adapt"}:
            continue
        if row["theme"] in used_themes:
            continue
        primary.append(row)
        used_themes.add(row["theme"])
        if len(primary) == 3:
            break
    return primary[:3]


def render_hotspot_block(index: int, row: dict) -> str:
    theme = row["theme"]
    return "\n".join(
        [
            f"### 热点 {index}",
            "",
            f"- 热点名称: {row['seed_name']}",
            f"- 来源平台: {row['platform']} ({row['link']})",
            f"- 为什么热: {reason_for(theme, row['views'], row['likes'], row['title'])}",
            f"- 为什么适合电摩: {fit_for(theme)}",
            f"- 推荐视频方向: {direction_for(theme)}",
            f"- 前 3 秒 Hook: {hook_for(theme)}",
            f"- 大概视频结构: {structure_for(theme)}",
            f"- 需要什么素材: {assets_for(theme)}",
            f"- TikTok 文案: {caption_tiktok(theme)}",
            f"- Instagram 文案: {caption_instagram(theme)}",
            f"- 封面大字: {cover_text(theme)}",
            f"- 评论区引导: {comments_for(theme)}",
            f"- 风险提醒: {row['risk_note']}",
            f"- 优先级: {priority_for(theme, row['views'], row['likes'])}",
            f"- 参考样本: @{row['author']} | {fmt_count(row['views'])} views | {fmt_count(row['likes'])} likes | {row['title']}",
            f"- 发布时间: {row.get('created_at', '')[:10]}",
            "",
        ]
    )


def render_watch_block(rows: list[dict]) -> str:
    lines = ["## 2. 可以观察的热点", ""]
    for row in rows[:5]:
        lines.append(f"- {row['seed_name']}: {row['heat']}; {row['best_channel']}; sample @{row['author']} ({fmt_count(row['views'])} views).")
    lines.append("")
    return "\n".join(lines)


def render_skip_block(rows: list[dict]) -> str:
    lines = ["## 3. 不建议蹭的热点", ""]
    if not rows:
        lines.append("- 暂无明显强蹭热点，但继续避免任何 police-chase、wheelie、非法上路、未成年危险骑行内容。")
        lines.append("")
        return "\n".join(lines)
    for row in rows[:5]:
        reason = row["risk_note"] if row["action"] == "risk" else "Current format feels forced for an e-moto account or would take too much setup."
        lines.append(f"- {row['seed_name']}: {reason} Sample @{row['author']} ({fmt_count(row['views'])} views).")
    lines.append("")
    return "\n".join(lines)


def render_topics(rows: list[dict]) -> str:
    themes = [row["theme"] for row in rows[:5]]
    options = {
        "fathers-day-gift": "父亲节车库惊喜开门反应",
        "garage-surprise": "配偶/家人把车藏进车库的揭晓视频",
        "summer-pov": "放学后/下班后夏天短骑 POV",
        "ride-pov": "私有地或合规路段的低风险地形 POV",
        "bike-wash": "泥车清洗前后反差",
        "bike-check-build": "车库 bike check + 部件近景",
    }
    lines = ["## 4. 今天可以直接拍的视频选题", ""]
    for theme in themes:
        lines.append(f"- {options[theme]}")
    if "fathers-day-gift" not in themes:
        lines.append("- 父亲节 gift angle 的车库封面短视频")
    if "bike-wash" not in themes:
        lines.append("- 一条 20-30 秒的 clean transformation")
    lines.append("")
    return "\n".join(lines)


def build_report(report_date: date, rows: list[dict]) -> str:
    top = select_top_recommendations(rows)
    watch = unique_by_theme(rows, {"watch", "adapt"})[3:8]
    risk_or_skip = [row for row in rows if row["action"] in {"risk", "skip"}]
    parts = [f"# {report_date.year}.{report_date.month}.{report_date.day} 外网热点候选池", ""]
    parts.append("注意：这是未验帧候选池，只能用来挑链接。最终报告必须先看视频帧，确认画面主体和内容类型。")
    parts.append("")
    parts.append("## 1. 需要人工验帧的候选")
    parts.append("")
    for idx, row in enumerate(top, start=1):
        parts.append(render_hotspot_block(idx, row))
    parts.append(render_watch_block(watch))
    parts.append(render_skip_block(risk_or_skip))
    parts.append(render_topics(top + watch))
    return "\n".join(parts).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the daily e-moto hotspot report.")
    parser.add_argument("--date", help="Report date in YYYY-MM-DD format. Defaults to today.")
    args = parser.parse_args()

    report_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_rows: list[dict] = []
    for seed in TREND_SEEDS:
        try:
            raw_rows.extend(fetch_tiktok_seed(seed))
        except Exception as exc:
            raw_rows.append(
                {
                    "seed_name": seed.name,
                    "query": seed.query,
                    "theme": seed.theme,
                    "platform": seed.platform_hint,
                    "author": "fetch-error",
                    "video_id": "",
                    "title": f"Fetch failed: {exc}",
                    "views": 0,
                    "likes": 0,
                    "link": "",
                }
            )

    recent_rows = [row for row in raw_rows if is_recent_2026(row, report_date)]
    rows = annotate(recent_rows)
    report_text = build_report(report_date, rows)

    stamp = report_date.strftime("%Y%m%d")
    report_path = OUTPUT_DIR / f"emoto_hotspot_report_{stamp}.md"
    json_path = OUTPUT_DIR / f"emoto_hotspot_candidates_{stamp}.json"
    report_path.write_text(report_text, encoding="utf-8")
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Report written to: {report_path}")
    print(f"Candidates written to: {json_path}")


if __name__ == "__main__":
    main()
