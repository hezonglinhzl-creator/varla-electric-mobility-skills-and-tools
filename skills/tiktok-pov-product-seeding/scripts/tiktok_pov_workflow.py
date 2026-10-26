from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gpt_provider import GptProviderError, generate_story_pack, load_openai_api_key


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}

BANNED_TERMS = [
    "dirt bike",
    "motorcycle",
    "motocross",
    "crazy fast",
    "insane speed",
    "dangerous",
    "race",
    "wheelie",
    "top speed",
    "max speed",
]

REPLACEMENTS = {
    "dirt bike": "off-road bike",
    "motorcycle": "off-road machine",
    "motocross": "off-road riding",
    "crazy fast": "smooth and powerful",
    "insane speed": "steady performance",
    "dangerous": "controlled",
    "race": "ride",
    "wheelie": "front-end lift",
    "top speed": "performance",
    "max speed": "performance",
}


@dataclass
class MediaFile:
    path: Path
    duration: float
    width: int | None = None
    height: int | None = None


BASE_BEATS: list[dict[str, Any]] = [
    {
        "type": "hook",
        "shot_intent": "hook",
        "duration": 3.0,
        "voiceover": "This caught my eye before I even turned it on.",
        "zh": "我还没开机，它就先抓住了我的注意力。",
        "segments": ["This caught my eye", "before I even", "turned it on"],
        "visual_action": "fast POV approach, hand enters frame, product shape teased",
        "audio_intent": "low BGM bed, tiny mechanical tick on reveal",
        "sfx": ["soft_tick"],
    },
    {
        "type": "reveal",
        "shot_intent": "reveal",
        "duration": 3.5,
        "voiceover": "The {product} has this quiet, heavy-duty look in person.",
        "zh": "{product} 实物看起来很安静，但很扎实。",
        "segments": ["The {product}", "has this quiet", "heavy-duty look"],
        "visual_action": "slow full reveal, keep product centered in vertical frame",
        "audio_intent": "BGM stays restrained, no commercial hit",
        "sfx": ["soft_reveal"],
    },
    {
        "type": "first_feel",
        "shot_intent": "detail",
        "duration": 4.0,
        "voiceover": "Up close, the frame, tires, and cockpit feel really solid.",
        "zh": "近看时，车架、轮胎和操控区都很有扎实感。",
        "segments": ["Up close", "the frame, tires", "and cockpit", "feel really solid"],
        "visual_action": "macro pass over frame, tire texture, handlebar/cockpit details",
        "audio_intent": "subtle texture sounds, keep original room tone",
        "sfx": ["metal_tap", "rubber_brush"],
    },
    {
        "type": "detail",
        "shot_intent": "interaction",
        "duration": 4.0,
        "voiceover": "I like when the small parts do not feel like an afterthought.",
        "zh": "我喜欢这种小部件也没有敷衍的感觉。",
        "segments": ["I like when", "the small parts", "do not feel", "like an afterthought"],
        "visual_action": "hand touches pedals, grips, display, brakes or hardware details",
        "audio_intent": "light tactile SFX as separate events",
        "sfx": ["switch_click", "metal_tap"],
    },
    {
        "type": "power_on",
        "shot_intent": "power_on",
        "duration": 3.0,
        "voiceover": "Then you power it on, and everything stays surprisingly calm.",
        "zh": "然后开机，整个感觉反而很安静、很稳。",
        "segments": ["Then you power it on", "and everything stays", "surprisingly calm"],
        "visual_action": "finger presses power, screen or lights wake up",
        "audio_intent": "brief BGM dip, isolated power-on SFX",
        "sfx": ["power_on"],
    },
    {
        "type": "silence_moment",
        "shot_intent": "silence_moment",
        "duration": 2.5,
        "voiceover": "No loud drama, just a smooth little wake-up moment.",
        "zh": "没有很夸张的动静，就是一个很顺的启动瞬间。",
        "segments": ["No loud drama", "just a smooth", "wake-up moment"],
        "visual_action": "hold a quiet close-up after power-on, let viewer feel silence",
        "audio_intent": "leave breathing space; environment sound stays audible",
        "sfx": [],
    },
    {
        "type": "power_moment",
        "shot_intent": "power_moment",
        "duration": 4.0,
        "voiceover": "On the first roll, the assist feels steady instead of twitchy.",
        "zh": "第一次轻推起来，助力感是稳的，不是很冲的那种。",
        "segments": ["On the first roll", "the assist feels steady", "instead of twitchy"],
        "visual_action": "slow first movement, wheel roll, suspension or tire response",
        "audio_intent": "BGM rises slightly; keep movement controlled",
        "sfx": ["tire_roll"],
    },
    {
        "type": "summary",
        "shot_intent": "mechanical_feedback",
        "duration": 2.0,
        "voiceover": "It is built for a fun ride, but it still feels controlled.",
        "zh": "它确实是为了好玩而做的，但整体还是有控制感。",
        "segments": ["built for", "a fun ride", "but still", "controlled"],
        "visual_action": "short action beat, no risky riding, show stable handling",
        "audio_intent": "controlled lift in BGM, no aggressive drop",
        "sfx": ["soft_whoosh"],
    },
    {
        "type": "closing",
        "shot_intent": "closing",
        "duration": 2.0,
        "voiceover": "That is the part I noticed most: it feels well built.",
        "zh": "我最明显的感受就是，它做得挺扎实。",
        "segments": ["That is the part", "I noticed most", "it feels", "well built"],
        "visual_action": "final product detail or parked beauty shot, no hard sell",
        "audio_intent": "BGM resolves cleanly",
        "sfx": ["soft_close"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a storyboard-first TikTok POV product seeding workflow.")
    parser.add_argument("--media-dir", required=True, help="Folder containing product video footage.")
    parser.add_argument("--output-dir", required=True, help="Output folder for generated workflow files.")
    parser.add_argument("--project-name", default="tiktok_pov_product_video")
    parser.add_argument("--product-name", default="off-road e-bike")
    parser.add_argument("--product-info", help="Optional UTF-8 JSON product brief.")
    parser.add_argument("--voiceover-source", help="Existing narration or voice reference file.")
    parser.add_argument("--voice-speed", type=float, default=1.0, help="Voiceover speed multiplier. Example: 1.2 for faster TikTok pacing.")
    parser.add_argument("--bgm-source", help="Optional BGM file.")
    parser.add_argument("--reference-video", help="Optional edited reference video used as one current style direction, not a permanent rule.")
    parser.add_argument("--style-preset", default="cinematic_pov_product_detail", help="Current style direction/preset name for this run.")
    parser.add_argument("--cosyvoice-root", default=r"D:\项目\Cosyvoice")
    parser.add_argument("--duration", type=float, default=28.0)
    parser.add_argument("--fit-duration-to-voiceover", action="store_true")
    parser.add_argument("--max-videos", type=int, default=60, help="Max source videos to probe.")
    parser.add_argument("--llm-provider", choices=["none", "openai"], default="none", help="Optional provider for script generation and compliance notes.")
    parser.add_argument("--openai-model", default="gpt-4.1-mini", help="OpenAI model name when --llm-provider openai is enabled.")
    parser.add_argument("--openai-api-key-env", default="OPENAI_API_KEY", help="Environment variable holding the OpenAI API key.")
    return parser.parse_args()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def probe_media(path: Path) -> MediaFile:
    try:
        payload = json.loads(
            run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration:stream=codec_type,width,height",
                    "-of",
                    "json",
                    str(path),
                ]
            ).stdout
        )
        duration = float(payload.get("format", {}).get("duration", 0.0) or 0.0)
        width = None
        height = None
        for stream in payload.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width", 0) or 0)
                height = int(stream.get("height", 0) or 0)
                break
        return MediaFile(path=path, duration=duration, width=width, height=height)
    except Exception:
        return MediaFile(path=path, duration=0.0)


def scan_media(media_dir: Path, max_videos: int) -> list[MediaFile]:
    files = [p for p in sorted(media_dir.iterdir()) if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    return [probe_media(p) for p in files[:max_videos]]


def audio_duration(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    return probe_media(path).duration


def adjusted_audio_duration(path: Path | None, speed: float) -> float | None:
    duration = audio_duration(path)
    if duration is None:
        return None
    if speed <= 0:
        raise ValueError("--voice-speed must be greater than 0")
    return duration / speed


def load_product_info(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return json.loads(p.read_text(encoding="utf-8"))


def scaled_beats(target_duration: float, product_name: str) -> list[dict[str, Any]]:
    base_total = sum(float(b["duration"]) for b in BASE_BEATS)
    scale = target_duration / base_total if base_total else 1.0
    beats: list[dict[str, Any]] = []
    for index, beat in enumerate(BASE_BEATS, start=1):
        cloned = dict(beat)
        cloned["id"] = index
        cloned["duration"] = round(float(beat["duration"]) * scale, 3)
        cloned["voiceover"] = str(cloned["voiceover"]).format(product=product_name)
        cloned["zh"] = str(cloned["zh"]).format(product=product_name)
        cloned["segments"] = [str(item).format(product=product_name) for item in cloned["segments"]]
        beats.append(cloned)
    drift = round(target_duration - sum(float(b["duration"]) for b in beats), 3)
    beats[-1]["duration"] = round(float(beats[-1]["duration"]) + drift, 3)
    return beats


def beat_skeleton_for_llm(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": beat["id"],
            "type": beat["type"],
            "shot_intent": beat["shot_intent"],
            "duration": beat["duration"],
            "default_voiceover": beat["voiceover"],
            "default_zh": beat["zh"],
            "default_segments": beat["segments"],
            "visual_action": beat["visual_action"],
            "audio_intent": beat["audio_intent"],
            "notes": "Match one visual beat per line and keep the tone non-commercial.",
        }
        for beat in beats
    ]


def normalize_gpt_beats(base_beats: list[dict[str, Any]], generated_beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {int(item.get("id")): item for item in generated_beats if str(item.get("id", "")).strip()}
    normalized: list[dict[str, Any]] = []
    for beat in base_beats:
        override = by_id.get(int(beat["id"]), {})
        subtitle_segments = override.get("subtitle_segments")
        if not isinstance(subtitle_segments, list) or not subtitle_segments:
            subtitle_segments = beat["segments"]
        normalized.append(
            {
                **beat,
                "voiceover": clean_script(str(override.get("voiceover") or beat["voiceover"]).strip()),
                "zh": str(override.get("zh") or beat["zh"]).strip(),
                "segments": [str(item).strip() for item in subtitle_segments if str(item).strip()],
                "visual_action": str(override.get("visual_action") or beat["visual_action"]).strip(),
                "audio_intent": str(override.get("audio_intent") or beat["audio_intent"]).strip(),
                "notes": str(override.get("notes") or "creator POV, no exaggerated claims, keep product detail evidence on screen").strip(),
            }
        )
    return normalized


def pick_video_for_beats(media: list[MediaFile], beats: list[dict[str, Any]]) -> list[MediaFile | None]:
    beat_count = len(beats)
    if not media:
        return [None] * beat_count
    selected: list[MediaFile | None] = []
    used: set[Path] = set()
    step = (len(media) - 1) / max(beat_count - 1, 1)
    for index, beat in enumerate(beats):
        preferred_index = int(round(index * step)) if len(media) > beat_count else index % len(media)
        needed = float(beat["duration"]) + 0.05
        ordered = media[preferred_index:] + media[:preferred_index]
        enough = next((item for item in ordered if item.path not in used and item.duration >= needed), None)
        if enough is None:
            enough = max((item for item in media if item.path not in used), key=lambda item: item.duration, default=None)
        if enough is None:
            enough = media[preferred_index % len(media)]
        selected.append(enough)
        used.add(enough.path)
    return selected


def clean_script(text: str) -> str:
    result = text
    lowered = result.lower()
    for term, replacement in REPLACEMENTS.items():
        if term in lowered:
            result = result.replace(term, replacement)
            lowered = result.lower()
    return result


def build_storyboard(project_name: str, duration: float, beats: list[dict[str, Any]], selected: list[MediaFile | None]) -> dict[str, Any]:
    timeline = 0.0
    out_beats = []
    for beat, media in zip(beats, selected):
        dur = float(beat["duration"])
        media_duration = media.duration if media else 0.0
        use_duration = min(dur, media_duration) if media_duration else dur
        out_beats.append(
            {
                "id": beat["id"],
                "type": beat["type"],
                "duration": dur,
                "timeline_start": round(timeline, 3),
                "voiceover": clean_script(beat["voiceover"]),
                "subtitle_segments": beat["segments"],
                "shot_intent": beat["shot_intent"],
                "visual_action": beat["visual_action"],
                "audio_intent": beat["audio_intent"],
                "sfx": beat["sfx"],
                "notes": "creator POV, no exaggerated claims, keep product detail evidence on screen",
                "selected_media": None
                if media is None
                else {
                    "file": str(media.path),
                    "source_duration": round(media.duration, 3),
                    "use_start": 0.0,
                    "use_duration": round(use_duration, 3),
                    "width": media.width,
                    "height": media.height,
                },
            }
        )
        timeline += dur
    return {
        "project_name": project_name,
        "style": "cinematic_pov_product_detail",
        "duration": round(duration, 3),
        "aspect_ratio": "9:16",
        "language": "en",
        "beats": out_beats,
    }


def srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - math.floor(seconds)) * 1000))
    if millis == 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - math.floor(seconds)) * 100))
    if centis == 100:
        secs += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def build_subtitles(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for beat in storyboard["beats"]:
        parts = beat["subtitle_segments"]
        if not parts:
            continue
        beat_start = float(beat["timeline_start"])
        beat_duration = float(beat["duration"])
        gap = 0.06 if len(parts) > 1 else 0.0
        available = max(0.2, beat_duration - gap * (len(parts) - 1))
        unit = available / len(parts)
        cursor = beat_start
        for i, text in enumerate(parts, start=1):
            dur = max(0.35, unit)
            cues.append(
                {
                    "beat_id": beat["id"],
                    "index_in_beat": i,
                    "text": text,
                    "start": round(cursor, 3),
                    "end": round(min(cursor + dur, beat_start + beat_duration), 3),
                    "duration": round(min(dur, beat_start + beat_duration - cursor), 3),
                    "caption_style": "phrase_breath_cut",
                }
            )
            cursor += dur + gap
    return cues


def build_srt(cues: list[dict[str, Any]]) -> str:
    blocks = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(f"{idx}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['text']}\n")
    return "\n".join(blocks)


def build_ass(cues: list[dict[str, Any]]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: POVTech,Montserrat SemiBold,72,&H00F3F7FF,&H00FFFFFF,&HAA061018,&H66000000,0,0,0,0,100,100,0,0,1,3,0,2,80,80,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cue in cues:
        safe = str(cue["text"]).replace("\n", r"\N")
        lines.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},POVTech,,0,0,0,,{{\\fad(80,80)}}{safe}")
    return header + "\n".join(lines) + "\n"


def compliance_report(script: str, cues: list[dict[str, Any]]) -> tuple[str, bool]:
    text = (script + "\n" + "\n".join(str(c["text"]) for c in cues)).lower()
    hits = [term for term in BANNED_TERMS if term in text]
    lines = [
        "# Compliance Report",
        "",
        f"Status: {'PASS' if not hits else 'REVIEW REQUIRED'}",
        "",
        "Checked areas:",
        "- English voiceover script",
        "- Rhythm subtitle segments",
        "- Banned high-risk claim terms",
        "",
    ]
    if hits:
        lines.append("Flagged terms:")
        lines.extend(f"- {term} -> prefer `{REPLACEMENTS.get(term, 'safer wording')}`" for term in hits)
    else:
        lines.append("No banned terms found.")
    lines.extend(
        [
            "",
            "Editorial reminders:",
            "- Keep performance language controlled and evidence-based.",
            "- Do not imply unsafe riding, speed testing, racing, or stunt use.",
            "- Keep the tone like a creator's first-person observation, not a product page.",
        ]
    )
    return "\n".join(lines) + "\n", not hits


def append_llm_compliance_summary(report: str, summary: str) -> str:
    summary = summary.strip()
    if not summary:
        return report
    return report.rstrip() + "\n\nModel review note:\n" + summary + "\n"


def build_atempo_filter(speed: float) -> str:
    if speed <= 0:
        raise ValueError("voice speed must be greater than 0")
    parts: list[float] = []
    remaining = speed
    while remaining > 2.0:
        parts.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        parts.append(0.5)
        remaining /= 0.5
    parts.append(remaining)
    return ",".join(f"atempo={part:.6g}" for part in parts)


def prepare_voiceover(source: Path | None, output_dir: Path, cosyvoice_root: Path, script_text: str, speed: float) -> dict[str, Any]:
    mp3_path = output_dir / "voiceover.mp3"
    wav_path = output_dir / "voiceover.wav"
    mode = "missing_source"
    if source and source.exists():
        if source.suffix.lower() == ".mp3" and abs(speed - 1.0) < 0.001:
            shutil.copy2(source, mp3_path)
        else:
            cmd = ["ffmpeg", "-y", "-i", str(source)]
            if abs(speed - 1.0) >= 0.001:
                cmd.extend(["-filter:a", build_atempo_filter(speed)])
            cmd.extend(["-codec:a", "libmp3lame", "-q:a", "2", str(mp3_path)])
            run(cmd)
        run(["ffmpeg", "-y", "-i", str(mp3_path), "-ar", "44100", "-ac", "1", str(wav_path)])
        mode = "copied_existing_voiceover_or_reference" if abs(speed - 1.0) < 0.001 else "retimed_existing_voiceover"
    else:
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", str(wav_path)])
        run(["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)])

    manifest = {
        "mode": mode,
        "voiceover_mp3": str(mp3_path),
        "voiceover_wav": str(wav_path),
        "source": str(source) if source else "",
        "voice_speed": speed,
        "cosyvoice_root": str(cosyvoice_root),
        "cosyvoice_available": cosyvoice_root.exists(),
        "recommended_next_step": "Use CosyVoice zero-shot or cloned voice generation only with authorized reference audio. Replace voiceover.mp3 after generation, then rerun captions if timing changes.",
        "script_text": script_text,
        "duration": audio_duration(mp3_path),
    }
    write_json(output_dir / "voiceover_manifest.json", manifest)
    return manifest


def write_style_reference_note(output_dir: Path, reference_video: Path | None, style_preset: str) -> None:
    lines = [
        "# Style Reference Note",
        "",
        f"Current style preset: {style_preset}",
        "",
        "This is one direction for the current project, not a permanent rule for the skill.",
        "",
        "Target feeling for this run: use the supplied CapCut/TikTok-native edited reference as a pacing and layer example, not as the only future style.",
        "",
        "Current style notes:",
        "- Use many independent short video segments on V1.",
        "- Keep a top POV caption layer near the upper third for the opening hook.",
        "- Use phrase captions that breathe with the narration; do not split every word mechanically.",
        "- Keep BGM as one continuous track.",
        "- Keep voiceover clips on their own audio track and allow speed changes such as 1.2x.",
        "- Add sparse SFX/glitch events as separate audio clips, not mixed into BGM.",
        "- Allow subtle video speed tags such as 0.8x, 1.0x, and 1.2x when they support the beat.",
        "- The tone should feel like POV creator footage: handheld, close product details, mechanical texture, controlled movement.",
        "",
        "Future style presets can replace this direction:",
        "- cinematic_quiet_detail",
        "- garage_mechanical_macro",
        "- night_ride_neon",
        "- clean_tech_hud",
        "- outdoor_trail_documentary",
        "- creator_vlog_review",
        "",
    ]
    if reference_video and reference_video.exists():
        info = probe_media(reference_video)
        lines.extend(
            [
                f"Reference video: {reference_video}",
                f"Reference duration: {info.duration:.3f}s",
                f"Reference size: {info.width}x{info.height}",
                "",
            ]
        )
    write_text(output_dir / "style_reference_note.md", "\n".join(lines))


def prepare_bgm(source: Path | None, output_dir: Path, duration: float) -> dict[str, Any]:
    bgm_file = ""
    if source and source.exists():
        target = output_dir / source.name
        shutil.copy2(source, target)
        bgm_file = str(target)
    metadata = {
        "file": bgm_file,
        "mood": "cinematic, restrained, mechanical, immersive",
        "bpm": "",
        "style": "low tension tech bed",
        "drop_points": [round(duration * 0.18, 2), round(duration * 0.58, 2)],
        "best_start_time": "0.0",
        "track_policy": "BGM is continuous main track; SFX must remain separate event tracks.",
    }
    write_json(output_dir / "bgm_selected.json", metadata)
    return metadata


def write_edit_plan(output_dir: Path, storyboard: dict[str, Any], bgm: dict[str, Any]) -> None:
    lines = [
        f"# Edit Plan: {storyboard['project_name']}",
        "",
        "Core rule: storyboard first, then voice, captions, shot alignment, BGM/SFX, and Jianying draft.",
        "",
        f"Duration: {storyboard['duration']}s",
        f"BGM: {bgm.get('file') or 'not selected'}",
        "",
        "| Beat | Time | Intent | Voiceover | Media | SFX |",
        "|---:|---:|---|---|---|---|",
    ]
    for beat in storyboard["beats"]:
        media = beat.get("selected_media") or {}
        media_name = Path(media.get("file", "")).name if media.get("file") else "manual pick needed"
        sfx = ", ".join(beat.get("sfx", [])) or "none"
        lines.append(
            f"| {beat['id']} | {beat['timeline_start']:.3f}-{beat['timeline_start'] + beat['duration']:.3f}s | {beat['shot_intent']} | {beat['voiceover']} | {media_name} | {sfx} |"
        )
    lines.extend(
        [
            "",
            "Jianying track plan:",
            "- Track V1: independent video segments per beat, not a flattened render.",
            "- Track A1: original/environment audio from video segments, kept low unless noisy.",
            "- Track A2: voiceover.mp3.",
            "- Track A3: BGM continuous main track.",
            "- Track A4+: independent SFX events for power-on, metal taps, tire roll, and soft transitions.",
            "- Text tracks: editable phrase captions, matching `subtitle_segments.json` and `captions.srt`.",
        ]
    )
    write_text(output_dir / "edit_plan.md", "\n".join(lines) + "\n")


def write_jianying_blueprint(output_dir: Path, storyboard: dict[str, Any], voice_manifest: dict[str, Any], bgm: dict[str, Any], cues: list[dict[str, Any]]) -> None:
    draft_dir = output_dir / "jianying_draft"
    draft_dir.mkdir(parents=True, exist_ok=True)
    video_segments = []
    sfx_events = []
    for beat in storyboard["beats"]:
        media = beat.get("selected_media") or {}
        video_segments.append(
            {
                "beat_id": beat["id"],
                "track": "V1",
                "source": media.get("file", ""),
                "timeline_start": beat["timeline_start"],
                "duration": beat["duration"],
                "source_start": media.get("use_start", 0.0),
                "source_duration": media.get("use_duration", beat["duration"]),
                "shot_intent": beat["shot_intent"],
                "visual_action": beat["visual_action"],
            }
        )
        for sfx in beat.get("sfx", []):
            sfx_events.append(
                {
                    "beat_id": beat["id"],
                    "track": "SFX",
                    "name": sfx,
                    "timeline_start": beat["timeline_start"],
                    "duration": min(0.8, beat["duration"]),
                    "status": "marker_only_add_source_later",
                }
            )
    blueprint = {
        "project_name": storyboard["project_name"],
        "aspect_ratio": storyboard["aspect_ratio"],
        "duration": storyboard["duration"],
        "tracks": {
            "video": video_segments,
            "voiceover": [{"track": "A2_voiceover", "source": voice_manifest.get("voiceover_mp3"), "start": 0, "duration": voice_manifest.get("duration")}],
            "bgm": [{"track": "A3_bgm", "source": bgm.get("file"), "start": 0, "duration": storyboard["duration"], "volume": 0.22}],
            "sfx": sfx_events,
            "captions": [{"track": "T1_captions", **cue} for cue in cues],
        },
        "safety": {
            "source_media_policy": "reference only; do not modify original files",
            "draft_policy": "create new draft; do not patch encrypted or open drafts in place",
        },
    }
    write_json(draft_dir / "draft_blueprint.json", blueprint)
    export_plan_beats = []
    for beat, segment in zip(storyboard["beats"], video_segments, strict=True):
        export_plan_beats.append(
            {
                "beat_id": f"beat_{int(beat['id']):04d}",
                "beat_type": beat["type"],
                "script_text": beat["voiceover"],
                "visual_goal": beat["visual_action"],
                "shot_note": beat["notes"],
                "timeline_start": beat["timeline_start"],
                "timeline_duration": beat["duration"],
                "selected_segments": [
                    {
                        "segment_id": f"segment_{int(beat['id']):04d}",
                        "video_path": segment["source"],
                        "use_start": segment["source_start"],
                        "use_duration": segment["source_duration"],
                        "selection_reason": beat["shot_intent"],
                    }
                ],
                "alternatives": [],
                "overlay_style": "pov_top_caption",
            }
        )
    write_json(
        draft_dir / "retrieval_plan.generated.json",
        {
            "project_name": storyboard["project_name"],
            "capcut_ratio": storyboard["aspect_ratio"],
            "style_preset": "current_run",
            "beats": export_plan_beats,
        },
    )
    write_json(
        draft_dir / "tts_manifest.generated.json",
        {
            "merged_audio_path": voice_manifest.get("voiceover_mp3"),
            "merged_audio_duration_ms": int(round((voice_manifest.get("duration") or storyboard["duration"]) * 1000)),
            "beats": [
                {
                    "beat_id": f"beat_{int(beat['id']):04d}",
                    "script_text": beat["voiceover"],
                    "narration_start_ms": int(round(beat["timeline_start"] * 1000)),
                    "audio_duration_ms": int(round(beat["duration"] * 1000)),
                    "timeline_start_ms": int(round(beat["timeline_start"] * 1000)),
                    "timeline_duration_ms": int(round(beat["duration"] * 1000)),
                    "duration_delta_ms": 0,
                    "words": [],
                }
                for beat in storyboard["beats"]
            ],
        },
    )


def html_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_hyperframes_overlay(output_dir: Path, cues: list[dict[str, Any]], duration: float) -> None:
    overlay_dir = output_dir / "hyperframes_overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    cue_divs = []
    for i, cue in enumerate(cues, start=1):
        cue_divs.append(
            f'<div id="cap-{i}" class="caption" data-start="{cue["start"]}" data-duration="{cue["duration"]}" data-track-index="1">{html_escape(str(cue["text"]))}</div>'
        )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TikTok POV Transparent Tech Overlay</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      background: transparent;
      overflow: hidden;
      font-family: "Montserrat", "Inter", "Arial", sans-serif;
    }}
    [data-composition-id="pov-tech-overlay"] {{
      width: 1080px;
      height: 1920px;
      position: relative;
      background: transparent;
      color: #f3f7ff;
    }}
    .hud {{
      position: absolute;
      inset: 0;
      border: 1px solid rgba(125, 211, 252, 0.18);
      box-shadow: inset 0 0 80px rgba(14, 165, 233, 0.08);
      pointer-events: none;
    }}
    .caption {{
      position: absolute;
      left: 84px;
      right: 84px;
      bottom: 250px;
      min-height: 92px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-size: 70px;
      line-height: 1.08;
      font-weight: 700;
      letter-spacing: 0;
      text-shadow: 0 4px 26px rgba(0, 0, 0, 0.72);
      opacity: 0;
      transform: translateY(24px) scale(0.985);
    }}
    .caption::after {{
      content: "";
      position: absolute;
      left: 18%;
      right: 18%;
      bottom: -20px;
      height: 2px;
      background: linear-gradient(90deg, transparent, rgba(125, 211, 252, 0.9), transparent);
      opacity: 0.8;
    }}
  </style>
</head>
<body>
  <div data-composition-id="pov-tech-overlay" data-width="1080" data-height="1920" data-start="0" data-duration="{duration}">
    <div class="hud"></div>
    {"".join(cue_divs)}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    const captions = Array.from(document.querySelectorAll(".caption"));
    captions.forEach((el) => {{
      const start = Number(el.dataset.start || 0);
      const duration = Number(el.dataset.duration || 0.8);
      tl.to(el, {{ opacity: 1, y: 0, scale: 1, duration: 0.16, ease: "power2.out" }}, start);
      tl.to(el, {{ opacity: 0, y: -18, duration: 0.16, ease: "power2.in" }}, Math.max(start + duration - 0.16, start + 0.18));
    }});
    window.__timelines["pov-tech-overlay"] = tl;
  </script>
</body>
</html>
"""
    write_text(overlay_dir / "index.html", html)
    write_text(
        overlay_dir / "DESIGN.md",
        "# Style Prompt\nTransparent cinematic tech HUD overlay for vertical POV product detail video.\n\n# Colors\n- Ice text: #f3f7ff\n- Cyan accent: #7dd3fc\n- Deep shadow: rgba(0,0,0,0.72)\n\n# Typography\nMontserrat or Inter, bold phrase captions.\n\n# What NOT to Do\nNo heavy cards, no sales banners, no speed or danger emphasis.\n",
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    media_dir = Path(args.media_dir)
    if not media_dir.exists():
        raise FileNotFoundError(media_dir)

    product_info = load_product_info(args.product_info)
    product_name = str(product_info.get("product_name") or args.product_name)
    voice_source = Path(args.voiceover_source) if args.voiceover_source else None
    voice_duration = adjusted_audio_duration(voice_source, args.voice_speed)
    target_duration = float(args.duration)
    if args.fit_duration_to_voiceover and voice_duration and voice_duration > 1:
        target_duration = voice_duration

    media = scan_media(media_dir, args.max_videos)
    beats = scaled_beats(target_duration, product_name)
    llm_summary = ""
    llm_status = {"provider": args.llm_provider, "enabled": False, "model": "", "error": ""}
    if args.llm_provider == "openai":
        api_key = load_openai_api_key(args.openai_api_key_env)
        if api_key:
            try:
                story_pack = generate_story_pack(
                    api_key=api_key,
                    model=args.openai_model,
                    product_name=product_name,
                    style_preset=args.style_preset,
                    duration=target_duration,
                    product_info=product_info,
                    beat_skeleton=beat_skeleton_for_llm(beats),
                )
                beats = normalize_gpt_beats(beats, story_pack.beats)
                llm_summary = story_pack.compliance_summary
                llm_status = {
                    "provider": "openai",
                    "enabled": True,
                    "model": args.openai_model,
                    "error": "",
                }
                write_json(
                    output_dir / "gpt_generation.json",
                    {
                        "provider": "openai",
                        "model": args.openai_model,
                        "beats": story_pack.beats,
                        "compliance_summary": story_pack.compliance_summary,
                    },
                )
            except GptProviderError as exc:
                llm_status = {
                    "provider": "openai",
                    "enabled": False,
                    "model": args.openai_model,
                    "error": str(exc),
                }
        else:
            llm_status = {
                "provider": "openai",
                "enabled": False,
                "model": args.openai_model,
                "error": f"Environment variable {args.openai_api_key_env} is not set.",
            }
    selected = pick_video_for_beats(media, beats)
    storyboard = build_storyboard(args.project_name, target_duration, beats, selected)

    script_en = "\n".join(beat["voiceover"] for beat in storyboard["beats"]) + "\n"
    script_zh = "\n".join(beat["zh"] for beat in beats) + "\n"
    cues = build_subtitles(storyboard)
    report, passed = compliance_report(script_en, cues)
    report = append_llm_compliance_summary(report, llm_summary)

    write_json(output_dir / "storyboard.json", storyboard)
    write_text(output_dir / "script_en.txt", script_en)
    write_text(output_dir / "script_zh.txt", script_zh)
    write_text(output_dir / "compliance_report.md", report)
    write_json(output_dir / "subtitle_segments.json", cues)
    write_text(output_dir / "captions.srt", build_srt(cues))
    write_text(output_dir / "word_or_phrase_captions.ass", build_ass(cues))

    voice_manifest = prepare_voiceover(voice_source, output_dir, Path(args.cosyvoice_root), script_en, args.voice_speed)
    bgm = prepare_bgm(Path(args.bgm_source) if args.bgm_source else None, output_dir, target_duration)
    write_edit_plan(output_dir, storyboard, bgm)
    write_jianying_blueprint(output_dir, storyboard, voice_manifest, bgm, cues)
    write_hyperframes_overlay(output_dir, cues, target_duration)
    write_style_reference_note(output_dir, Path(args.reference_video) if args.reference_video else None, args.style_preset)

    status = {
        "status": "PASS" if passed else "REVIEW_REQUIRED",
        "output_dir": str(output_dir),
        "storyboard_duration": target_duration,
        "voiceover_duration": voice_manifest.get("duration"),
        "media_files_scanned": len(media),
        "llm": llm_status,
        "files": [
            "storyboard.json",
            "script_en.txt",
            "script_zh.txt",
            "compliance_report.md",
            "subtitle_segments.json",
            "captions.srt",
            "word_or_phrase_captions.ass",
            "voiceover.mp3",
            "voiceover.wav",
            "voiceover_manifest.json",
            "bgm_selected.json",
            "edit_plan.md",
            "jianying_draft/draft_blueprint.json",
            "hyperframes_overlay/index.html",
            "style_reference_note.md",
        ],
    }
    if llm_status.get("enabled"):
        status["files"].append("gpt_generation.json")
    write_json(output_dir / "workflow_status.json", status)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
