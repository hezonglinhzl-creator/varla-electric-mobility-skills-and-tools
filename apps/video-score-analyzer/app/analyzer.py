from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


@dataclass
class Paths:
    root: Path
    uploads: Path
    reports: Path
    exports: Path


def ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Missing required tool: {name}. Please install FFmpeg and add it to PATH.")
    return path


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")
    return json.loads(result.stdout or "{}")


def run_command(command: list[str], timeout: int = 180) -> None:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")


def probe_video(video_path: Path) -> dict[str, Any]:
    ffprobe = ensure_tool("ffprobe")
    data = run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(video_path),
        ]
    )
    streams = data.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    duration = float(video_stream.get("duration") or data.get("format", {}).get("duration") or 0)
    fps = parse_fps(str(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1"))
    size_bytes = int(data.get("format", {}).get("size") or video_path.stat().st_size)
    aspect_ratio = ratio_label(width, height)
    vertical_916 = is_vertical_916(width, height)
    return {
        "file_name": video_path.name,
        "file_size_mb": round(size_bytes / 1024 / 1024, 2),
        "duration_seconds": round(duration, 2),
        "duration_label": seconds_label(duration),
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}" if width and height else "Unknown",
        "fps": round(fps, 2),
        "aspect_ratio": aspect_ratio,
        "is_vertical_9_16": vertical_916,
        "has_audio": audio_stream is not None,
        "video_codec": video_stream.get("codec_name", "unknown"),
        "audio_codec": audio_stream.get("codec_name", "none") if audio_stream else "none",
    }


def parse_fps(value: str) -> float:
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    left, right = value.split("/", 1)
    try:
        return float(left) / max(float(right), 1.0)
    except ValueError:
        return 0.0


def ratio_label(width: int, height: int) -> str:
    if not width or not height:
        return "Unknown"
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def is_vertical_916(width: int, height: int) -> bool:
    if not width or not height:
        return False
    return height >= width and abs((width / height) - (9 / 16)) < 0.04


def seconds_label(seconds: float) -> str:
    minutes = int(seconds // 60)
    rest = seconds - minutes * 60
    return f"{minutes:02d}:{rest:05.2f}"


def score_to_level(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Risky"
    return "Needs recut"


def clamp(value: float, low: float = 0, high: float = 100) -> int:
    return int(max(low, min(high, round(value))))


def sample_times(duration: float) -> list[float]:
    times: list[float] = []
    current = 0.0
    while current <= min(duration, 3.0) + 0.001:
        times.append(round(current, 2))
        current += 0.25
    current = 3.5
    while current <= duration + 0.001:
        times.append(round(current, 2))
        current += 0.5
    return sorted(set(times))


def extract_frame(video_path: Path, frame_path: Path, timestamp: float) -> None:
    ffmpeg = ensure_tool("ffmpeg")
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(frame_path),
        ],
        timeout=60,
    )


def image_metrics(frame_path: Path) -> dict[str, Any]:
    with Image.open(frame_path) as image:
        image = image.convert("RGB")
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        brightness = stat.mean[0]
        contrast = stat.stddev[0]
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        sharpness = edge_stat.mean[0] + edge_stat.stddev[0]
        width, height = image.size
        center = image.crop((width * 0.22, height * 0.18, width * 0.78, height * 0.82))
        center_stat = ImageStat.Stat(center.convert("L"))
        center_activity = center_stat.stddev[0]
    brightness_score = clamp(100 - abs(brightness - 125) * 0.75)
    clarity_score = clamp(sharpness * 1.9)
    contrast_score = clamp(contrast * 2.2)
    subject_score = clamp(center_activity * 2.5)
    composition_score = clamp((brightness_score * 0.25) + (contrast_score * 0.35) + (subject_score * 0.4))
    product_score = clamp(subject_score * 0.75 + contrast_score * 0.25)
    visual_score = clamp(clarity_score * 0.35 + composition_score * 0.35 + contrast_score * 0.3)
    usability_score = clamp(clarity_score * 0.35 + composition_score * 0.25 + product_score * 0.25 + brightness_score * 0.15)
    return {
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "sharpness": round(sharpness, 2),
        "clarity_score": clarity_score,
        "composition_score": composition_score,
        "product_exposure_score": product_score,
        "visual_hook_score": visual_score,
        "ad_usability_score": usability_score,
    }


def frame_difference(left: Path | None, right: Path) -> float:
    if left is None:
        return 0.0
    with Image.open(left) as a, Image.open(right) as b:
        a = a.convert("L").resize((96, 170))
        b = b.convert("L").resize((96, 170))
        diff = ImageChops.difference(a, b)
        stat = ImageStat.Stat(diff)
        return round(stat.mean[0], 2)


def extract_audio_waveform(video_path: Path, job_dir: Path, duration: float) -> dict[str, Any]:
    if duration <= 0:
        return {"samples": [], "silent_ranges": []}
    ffmpeg = ensure_tool("ffmpeg")
    audio_path = job_dir / "audio.wav"
    try:
        run_command(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(audio_path),
            ],
            timeout=120,
        )
    except Exception:
        return {"samples": [], "silent_ranges": []}

    samples: list[dict[str, Any]] = []
    silent_ranges: list[dict[str, float]] = []
    with wave.open(str(audio_path), "rb") as wav:
        rate = wav.getframerate()
        width = wav.getsampwidth()
        frames_per_bucket = max(1, int(rate * 0.25))
        total = wav.getnframes()
        cursor = 0
        silent_start: float | None = None
        while cursor < total:
            raw = wav.readframes(frames_per_bucket)
            if not raw:
                break
            values = bytes_to_samples(raw, width)
            rms = math.sqrt(sum(v * v for v in values) / max(1, len(values))) if values else 0
            level = min(1.0, rms / 22000)
            time_pos = cursor / rate
            is_silent = level < 0.018
            samples.append({"time": round(time_pos, 2), "level": round(level, 3)})
            if is_silent and silent_start is None:
                silent_start = time_pos
            if not is_silent and silent_start is not None:
                if time_pos - silent_start >= 0.7:
                    silent_ranges.append({"start": round(silent_start, 2), "end": round(time_pos, 2)})
                silent_start = None
            cursor += frames_per_bucket
        if silent_start is not None and duration - silent_start >= 0.7:
            silent_ranges.append({"start": round(silent_start, 2), "end": round(duration, 2)})
    return {"samples": samples, "silent_ranges": silent_ranges[:10]}


def bytes_to_samples(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [b - 128 for b in raw]
    if sample_width == 2:
        return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw) - 1, 2)]
    if sample_width == 4:
        return [int.from_bytes(raw[i : i + 4], "little", signed=True) / 65536 for i in range(0, len(raw) - 3, 4)]
    return []


def analyze_video(video_path: Path, paths: Paths) -> dict[str, Any]:
    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("Unsupported video type. Use mp4, mov, m4v, or webm.")

    video_info = probe_video(video_path)
    duration = float(video_info["duration_seconds"])
    job_id = hashlib.sha1(f"{video_path.name}-{video_path.stat().st_mtime_ns}".encode("utf-8")).hexdigest()[:12]
    job_dir = paths.reports / job_id
    frames_dir = job_dir / "frames"
    job_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    frames: list[dict[str, Any]] = []
    prev_path: Path | None = None
    for index, timestamp in enumerate(sample_times(duration), start=1):
        frame_path = frames_dir / f"frame_{index:03d}_{timestamp:.2f}s.jpg"
        try:
            extract_frame(video_path, frame_path, timestamp)
            metrics = image_metrics(frame_path)
            diff = frame_difference(prev_path, frame_path)
            prev_path = frame_path
            frames.append(
                {
                    "index": index,
                    "time": timestamp,
                    "time_label": seconds_label(timestamp),
                    "image_url": f"/reports/{job_id}/frames/{frame_path.name}",
                    "change_score": diff,
                    **metrics,
                }
            )
        except Exception as exc:
            frames.append({"index": index, "time": timestamp, "time_label": seconds_label(timestamp), "error": str(exc)})

    audio = extract_audio_waveform(video_path, job_dir, duration) if video_info["has_audio"] else {"samples": [], "silent_ranges": []}
    shots = detect_shots(frames, duration)
    scores = score_video(video_info, frames, audio, shots)
    report = build_report(video_info, frames, shots, audio, scores, job_id, paths)
    write_outputs(report, paths)
    return report


def detect_shots(frames: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    usable_frames = [frame for frame in frames if "error" not in frame]
    changes = [float(frame.get("change_score", 0)) for frame in usable_frames if float(frame.get("time", 0)) > 0.2]
    avg_change = average(changes)
    variance = average([(value - avg_change) ** 2 for value in changes]) if changes else 0
    dynamic_threshold = max(24.0, avg_change + math.sqrt(variance) * 1.2)
    cuts = [0.0]
    for frame in usable_frames:
        timestamp = float(frame.get("time", 0))
        if timestamp <= 0.2 or timestamp >= duration - 0.2:
            continue
        min_gap = 0.55 if timestamp <= 3.0 else 1.15
        if frame.get("change_score", 0) >= dynamic_threshold and timestamp - cuts[-1] >= min_gap:
            cuts.append(timestamp)
    cuts.append(duration)
    cuts = sorted(set(cuts))
    shots: list[dict[str, Any]] = []
    for index in range(len(cuts) - 1):
        start = cuts[index]
        end = cuts[index + 1]
        if end - start < 0.2:
            continue
        matching = [frame for frame in frames if start <= float(frame.get("time", 0)) <= end]
        avg_score = average([frame.get("ad_usability_score", 0) for frame in matching])
        representative = representative_frame(matching, start, end)
        shots.append(
            {
                "index": len(shots) + 1,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(end - start, 2),
                "score": clamp(avg_score),
                "keep": avg_score >= 62 or start < 3,
                "frame_url": representative.get("image_url", "") if representative else "",
                "frame_time": representative.get("time_label", "") if representative else "",
                "issue": shot_issue(start, end, avg_score, representative),
                "suggestion": shot_suggestion(start, end, avg_score, representative),
            }
        )
    return shots


def representative_frame(frames: list[dict[str, Any]], start: float, end: float) -> dict[str, Any] | None:
    if not frames:
        return None
    midpoint = start + (end - start) / 2
    return min(frames, key=lambda frame: abs(float(frame.get("time", midpoint)) - midpoint))


def average(values: list[Any]) -> float:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numbers) / len(numbers) if numbers else 0.0


def shot_issue(start: float, end: float, score: float, frame: dict[str, Any] | None) -> str:
    duration = end - start
    product = float(frame.get("product_exposure_score", score)) if frame else score
    clarity = float(frame.get("clarity_score", score)) if frame else score
    brightness = float(frame.get("brightness", 125)) if frame else 125
    if start == 0 and duration > 2.4:
        return "开头镜头偏长，前 3 秒容易显得慢。"
    if duration > 4.2:
        return "单个镜头太长，短视频投流容易拖节奏。"
    if duration < 0.45:
        return "镜头很短，可能只是画面变化点，不一定是有效内容。"
    if score < 55:
        return "画面可用性偏低，清晰度、曝光或主体不够稳。"
    if product < 58:
        return "产品主体不够突出，观众可能不知道重点看哪里。"
    if clarity < 58:
        return "画面清晰度偏弱，细节不够利于投流。"
    if brightness < 70:
        return "画面偏暗，需要提亮或换更清楚的镜头。"
    if brightness > 190:
        return "画面偏亮，可能有过曝风险。"
    return "这个镜头基础可用，主要看是否承担卖点或情绪价值。"


def shot_suggestion(start: float, end: float, score: float, frame: dict[str, Any] | None) -> str:
    duration = end - start
    product = float(frame.get("product_exposure_score", score)) if frame else score
    if start < 1 and score < 70:
        return "建议把更清楚的整车、骑行动作或冲击画面提前到 0.5 秒内。"
    if start == 0 and duration > 2.4:
        return "建议从这个镜头里只保留最有冲击力的 0.8-1.5 秒，并加英文钩子字幕。"
    if duration > 4.2:
        return "建议压缩到 1-2 秒，只留产品最清楚或动作最强的一段。"
    if duration < 0.45:
        return "如果这不是故意卡点，可以和前后镜头合并，不要单独当核心镜头。"
    if score < 55:
        return "除非它证明关键卖点，否则建议删除或替换为更亮、更稳、更近的画面。"
    if product < 58:
        return "建议补一个近景或整车完整露出的镜头，让车、轮胎、电池/避震等卖点更明确。"
    return "可保留。建议配一句短英文字幕，把这个镜头承担的卖点说清楚。"


def score_video(video_info: dict[str, Any], frames: list[dict[str, Any]], audio: dict[str, Any], shots: list[dict[str, Any]]) -> dict[str, Any]:
    golden_frames = [frame for frame in frames if float(frame.get("time", 99)) <= 3.0 and "error" not in frame]
    all_frames = [frame for frame in frames if "error" not in frame]
    first_second = [frame for frame in golden_frames if float(frame["time"]) <= 1.0]
    change_first3 = average([frame.get("change_score", 0) for frame in golden_frames])
    clarity = average([frame.get("clarity_score", 0) for frame in all_frames])
    visual = average([frame.get("visual_hook_score", 0) for frame in all_frames])
    product = average([frame.get("product_exposure_score", 0) for frame in all_frames])
    golden_visual = average([frame.get("visual_hook_score", 0) for frame in golden_frames])
    first_second_product = average([frame.get("product_exposure_score", 0) for frame in first_second])
    golden_score = clamp(golden_visual * 0.45 + first_second_product * 0.25 + min(100, change_first3 * 3.2) * 0.2 + audio_hook_score(audio) * 0.1)
    structure_score = score_structure(video_info, shots)
    rhythm_score = score_rhythm(video_info, shots)
    emotional_score = clamp(visual * 0.6 + min(100, change_first3 * 3.5) * 0.4)
    platform_score = score_platform(video_info, golden_score, rhythm_score, clarity)
    cta_score = clamp(55 + (10 if video_info["duration_seconds"] <= 20 else 0) + (10 if golden_score >= 75 else 0))
    total = clamp(
        golden_score * 0.25
        + structure_score * 0.15
        + rhythm_score * 0.15
        + product * 0.15
        + emotional_score * 0.1
        + clarity * 0.1
        + platform_score["average"] * 0.05
        + cta_score * 0.05
    )
    biggest_problem = biggest_issue(video_info, golden_score, product, rhythm_score, clarity)
    return {
        "total": total,
        "level": score_to_level(total),
        "advice": delivery_advice(total),
        "biggest_problem": biggest_problem,
        "priority_fix": priority_fix(biggest_problem),
        "dimensions": {
            "golden_3s": explain_score(golden_score, "Opening strength and first-three-second retention."),
            "structure": explain_score(structure_score, "Whether the video has a clear short-form ad structure."),
            "rhythm": explain_score(rhythm_score, "Shot length and cut frequency."),
            "product_exposure": explain_score(product, "How clearly the product appears in sampled frames."),
            "emotional_value": explain_score(emotional_score, "Movement, scene energy, and visual interest."),
            "visual_quality": explain_score(clarity, "Sharpness, exposure, and contrast."),
            "platform_fit": explain_score(platform_score["average"], "Fit for TikTok, Reels, and Shorts."),
            "cta_conversion": explain_score(cta_score, "CTA and conversion potential placeholder for MVP."),
        },
        "platforms": platform_score,
        "golden_3s": golden_three_seconds(golden_score, golden_frames, audio),
    }


def audio_hook_score(audio: dict[str, Any]) -> int:
    early = [item["level"] for item in audio.get("samples", []) if item.get("time", 99) <= 3]
    if not early:
        return 45
    return clamp(average(early) * 250)


def score_structure(video_info: dict[str, Any], shots: list[dict[str, Any]]) -> int:
    duration = float(video_info["duration_seconds"])
    if duration <= 0:
        return 0
    shot_count = len(shots)
    target = 6 if duration <= 15 else 10
    count_score = 100 - abs(shot_count - target) * 8
    first_cut = shots[0]["duration"] if shots else duration
    opening_score = 95 if first_cut <= 2.0 else 70 if first_cut <= 3.5 else 48
    return clamp(count_score * 0.55 + opening_score * 0.45)


def score_rhythm(video_info: dict[str, Any], shots: list[dict[str, Any]]) -> int:
    if not shots:
        return 0
    avg_len = average([shot["duration"] for shot in shots])
    if avg_len <= 0:
        return 0
    ideal = 1.6 if video_info["duration_seconds"] <= 15 else 2.2
    return clamp(100 - abs(avg_len - ideal) * 22)


def score_platform(video_info: dict[str, Any], golden: int, rhythm: int, clarity: float) -> dict[str, Any]:
    vertical_bonus = 12 if video_info["is_vertical_9_16"] else -18
    duration = float(video_info["duration_seconds"])
    length_bonus = 8 if 6 <= duration <= 30 else -10
    tiktok = clamp(golden * 0.5 + rhythm * 0.25 + clarity * 0.15 + vertical_bonus + length_bonus)
    reels = clamp(clarity * 0.4 + rhythm * 0.25 + golden * 0.2 + vertical_bonus + length_bonus)
    shorts = clamp(golden * 0.25 + rhythm * 0.25 + clarity * 0.25 + vertical_bonus + (8 if duration <= 60 else -15))
    return {
        "tiktok": platform_detail(tiktok, "Strong first second, real feeling, comment hook."),
        "instagram_reels": platform_detail(reels, "Clean visual quality, cover frame, lifestyle feeling."),
        "youtube_shorts": platform_detail(shorts, "Clear structure, watchability, title and cover support."),
        "average": clamp((tiktok + reels + shorts) / 3),
    }


def platform_detail(score: int, focus: str) -> dict[str, Any]:
    return {
        "score": score,
        "focus": focus,
        "recommended_length": "6-15s for ads, 15-30s for seeding.",
        "subtitle_style": "Short, high-contrast English captions.",
        "cta": "Ask a specific riding or product question instead of a generic Buy Now.",
    }


def explain_score(score: float, reason: str) -> dict[str, Any]:
    return {"score": clamp(score), "level": score_to_level(score), "reason": reason}


def golden_three_seconds(score: int, frames: list[dict[str, Any]], audio: dict[str, Any]) -> dict[str, Any]:
    product_first = next((frame["time"] for frame in frames if frame.get("product_exposure_score", 0) >= 62), None)
    low_frames = [frame for frame in frames if frame.get("ad_usability_score", 100) < 58]
    issue = "Opening is usable."
    if product_first is None or product_first > 1.0:
        issue = "Product or clear subject appears too late for paid traffic."
    elif low_frames:
        issue = "Some opening frames are weak or unclear."
    risk = "Low" if score >= 80 else "Medium" if score >= 62 else "High"
    return {
        "score": score,
        "risk": risk,
        "biggest_issue": issue,
        "product_first_seen": product_first,
        "sound_hook": "Detected" if audio_hook_score(audio) >= 60 else "Weak or unavailable",
        "rewrite_opening": [
            "0-0.5s: Start with the complete bike or strongest riding action.",
            "0.5-1.5s: Add one direct English hook caption about speed, battery, or weekend riding.",
            "1.5-3s: Show proof shot: wheel, suspension, rider reaction, or terrain pass.",
        ],
    }


def biggest_issue(video_info: dict[str, Any], golden: int, product: float, rhythm: int, clarity: float) -> str:
    if not video_info["is_vertical_9_16"]:
        return "Video is not 9:16 vertical."
    if golden < 65:
        return "First 3 seconds are not strong enough."
    if product < 58:
        return "Product is not prominent enough."
    if rhythm < 58:
        return "Rhythm is too slow or uneven."
    if clarity < 58:
        return "Visual quality needs improvement."
    return "Main structure is usable; optimize copy and CTA."


def priority_fix(issue: str) -> str:
    mapping = {
        "Video is not 9:16 vertical.": "Crop or re-export as 1080x1920 before paid traffic.",
        "First 3 seconds are not strong enough.": "Move product/action into the first 0.5-1.0 seconds and remove empty opening footage.",
        "Product is not prominent enough.": "Use closer product shots and keep the bike unobstructed in key frames.",
        "Rhythm is too slow or uneven.": "Trim long shots; target one useful visual beat every 1-2 seconds.",
        "Visual quality needs improvement.": "Replace blurred/dark shots and export with higher bitrate.",
    }
    return mapping.get(issue, "Add a clearer CTA and test a 6s/15s cut.")


def delivery_advice(total: int) -> str:
    if total >= 85:
        return "Can test paid traffic; still A/B test opening caption and cover."
    if total >= 72:
        return "Can test after optimizing the opening 3 seconds."
    if total >= 60:
        return "Use for organic first; paid traffic risk is medium to high."
    return "Not recommended for paid traffic before recut."


def build_report(
    video_info: dict[str, Any],
    frames: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    audio: dict[str, Any],
    scores: dict[str, Any],
    job_id: str,
    paths: Paths,
) -> dict[str, Any]:
    created_at = datetime.now().isoformat(timespec="seconds")
    return {
        "job_id": job_id,
        "created_at": created_at,
        "video": video_info,
        "scores": scores,
        "frames": frames,
        "shots": shots,
        "audio": audio,
        "exports": {
            "json": f"/exports/{job_id}.json",
            "markdown": f"/exports/{job_id}.md",
            "csv": f"/exports/{job_id}_frames.csv",
        },
        "architecture_note": "MVP material score uses local FFmpeg and heuristic scoring. It is not actual market performance unless calibrated with publishing data.",
    }


def write_outputs(report: dict[str, Any], paths: Paths) -> None:
    job_id = report["job_id"]
    (paths.exports / f"{job_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (paths.exports / f"{job_id}.md").write_text(markdown_report(report), encoding="utf-8")
    with (paths.exports / f"{job_id}_frames.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "time",
                "clarity_score",
                "composition_score",
                "product_exposure_score",
                "visual_hook_score",
                "ad_usability_score",
                "change_score",
                "image_url",
            ],
        )
        writer.writeheader()
        for frame in report["frames"]:
            writer.writerow({field: frame.get(field, "") for field in writer.fieldnames})


def markdown_report(report: dict[str, Any]) -> str:
    video = report["video"]
    scores = report["scores"]
    lines = [
        f"# Video Score Report - {video['file_name']}",
        "",
        f"- Material check score: {scores['total']} / 100",
        f"- Material-only advice: {scores['advice']}",
        "- Note: this score is based on local visual/rhythm heuristics, not real views, retention, or engagement.",
        f"- Biggest problem: {scores['biggest_problem']}",
        f"- Priority fix: {scores['priority_fix']}",
        f"- Duration: {video['duration_label']}",
        f"- Resolution: {video['resolution']} ({video['aspect_ratio']})",
        f"- 9:16 vertical: {'Yes' if video['is_vertical_9_16'] else 'No'}",
        f"- Audio: {'Yes' if video['has_audio'] else 'No'}",
        "",
        "## Golden 3 Seconds",
        "",
        f"- Score: {scores['golden_3s']['score']}",
        f"- Swipe risk: {scores['golden_3s']['risk']}",
        f"- Main issue: {scores['golden_3s']['biggest_issue']}",
        "",
        "## Shot Suggestions",
        "",
        "| # | Time | Score | Keep | Frame | Issue | Suggestion |",
        "|---|---|---:|---|---|---|---|",
    ]
    for shot in report["shots"]:
        lines.append(
            f"| {shot['index']} | {shot['start']}-{shot['end']}s | {shot['score']} | "
            f"{'Yes' if shot['keep'] else 'No'} | {shot.get('frame_time', '')} | {shot['issue']} | {shot['suggestion']} |"
        )
    return "\n".join(lines) + "\n"
