from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


@dataclass
class MediaItem:
    path: Path
    duration: float
    index: int
    fingerprint: int
    group_id: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a multi-shot Jianying plan aligned to voiceover/BGM audio peaks.")
    parser.add_argument("--media-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--voiceover-wav", required=True)
    parser.add_argument("--bgm-path")
    parser.add_argument("--draft-plan-out", default="jianying_draft/retrieval_plan.peak_matched.generated.json")
    parser.add_argument("--max-videos", type=int, default=96)
    parser.add_argument("--min-shot-duration", type=float, default=0.72)
    parser.add_argument("--max-shot-duration", type=float, default=1.45)
    return parser.parse_args()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def probe_duration(path: Path) -> float:
    try:
        out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def hamming(a: int, b: int) -> int:
    return int((a ^ b).bit_count())


def video_fingerprint(path: Path, duration: float) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        frame_path = Path(tmp) / "frame.jpg"
        ss = max(0.1, min(duration * 0.45, max(duration - 0.2, 0.1)))
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=17:16:force_original_aspect_ratio=decrease,pad=17:16:-1:-1:color=black", str(frame_path)])
            img = Image.open(frame_path).convert("L").resize((17, 16))
            arr = np.array(img, dtype=np.int16)
            diff = arr[:, 1:] > arr[:, :-1]
            value = 0
            for bit in diff.flatten()[:128]:
                value = (value << 1) | int(bit)
            return value
        except Exception:
            return abs(hash(path.name)) & ((1 << 128) - 1)


def assign_group(fingerprint: int, groups: list[int], threshold: int = 12) -> int:
    for idx, fp in enumerate(groups):
        if hamming(fingerprint, fp) <= threshold:
            return idx
    groups.append(fingerprint)
    return len(groups) - 1


def scan_media(media_dir: Path, max_videos: int) -> list[MediaItem]:
    paths = [p for p in sorted(media_dir.iterdir()) if p.is_file() and p.suffix.lower() in VIDEO_EXTS][:max_videos]
    groups: list[int] = []
    items: list[MediaItem] = []
    for index, path in enumerate(paths):
        duration = probe_duration(path)
        if duration <= 0.35:
            continue
        fp = video_fingerprint(path, duration)
        group_id = assign_group(fp, groups)
        items.append(MediaItem(path=path, duration=duration, index=index, fingerprint=fp, group_id=group_id))
    return items


def load_audio_mono(path: Path) -> tuple[np.ndarray, int]:
    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "audio.f32"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "44100", "-f", "f32le", str(raw_path)])
        audio = np.fromfile(raw_path, dtype=np.float32)
    return audio, 44100


def rms_envelope(audio: np.ndarray, sample_rate: int, window_ms: int = 80) -> tuple[np.ndarray, float]:
    window = max(1, int(sample_rate * window_ms / 1000))
    usable = len(audio) - (len(audio) % window)
    if usable <= 0:
        return np.array([], dtype=np.float32), window / sample_rate
    framed = audio[:usable].reshape(-1, window)
    env = np.sqrt(np.mean(np.square(framed), axis=1))
    return env, window / sample_rate


def local_peak_times(audio_path: Path) -> list[float]:
    audio, sr = load_audio_mono(audio_path)
    env, step = rms_envelope(audio, sr)
    if env.size == 0:
        return []
    threshold = max(float(np.percentile(env, 72)), float(env.mean() + env.std() * 0.35))
    peaks: list[float] = []
    last = -999.0
    for i in range(1, len(env) - 1):
        if env[i] >= threshold and env[i] >= env[i - 1] and env[i] >= env[i + 1]:
            t = i * step
            if t - last >= 0.42:
                peaks.append(round(t, 3))
                last = t
    return peaks


def shot_count(duration: float, min_shot: float, max_shot: float, beat_type: str) -> int:
    base = max(2, int(round(duration / 1.05)))
    if beat_type in {"detail", "first_feel", "power_moment"}:
        base += 1
    if beat_type in {"silence_moment", "closing"}:
        base = max(2, base - 1)
    return max(2, min(4, base, int(duration / min_shot)))


def choose_boundaries(start: float, duration: float, peaks: list[float], count: int, min_shot: float) -> list[float]:
    if count <= 1:
        return [start, start + duration]
    boundaries = [start]
    for slot in range(1, count):
        ideal = start + duration * slot / count
        candidates = [
            peak
            for peak in peaks
            if start + min_shot <= peak <= start + duration - min_shot
            and all(abs(peak - b) >= min_shot for b in boundaries)
        ]
        chosen = min(candidates, key=lambda peak: abs(peak - ideal), default=ideal)
        if chosen - boundaries[-1] < min_shot:
            chosen = boundaries[-1] + min_shot
        boundaries.append(round(chosen, 3))
    boundaries.append(round(start + duration, 3))
    boundaries = sorted(boundaries)
    repaired = [boundaries[0]]
    for b in boundaries[1:]:
        if b - repaired[-1] < min_shot and b != boundaries[-1]:
            continue
        repaired.append(b)
    if repaired[-1] != round(start + duration, 3):
        repaired.append(round(start + duration, 3))
    return repaired


def pool_for_intent(items: list[MediaItem], intent: str) -> list[MediaItem]:
    n = max(1, len(items))
    if intent in {"hook", "reveal"}:
        lo, hi = 0.00, 0.40
    elif intent in {"detail", "interaction", "power_on", "silence_moment"}:
        lo, hi = 0.12, 0.78
    else:
        lo, hi = 0.45, 1.00
    selected = [item for item in items if lo <= item.index / n <= hi]
    return selected or items


def select_media(pool: list[MediaItem], used_files: set[Path], used_groups: set[int], needed: float) -> MediaItem:
    candidates = [item for item in pool if item.path not in used_files and item.group_id not in used_groups and item.duration >= needed + 0.12]
    if not candidates:
        candidates = [item for item in pool if item.path not in used_files and item.duration >= needed + 0.12]
    if not candidates:
        candidates = [item for item in pool if item.path not in used_files]
    if not candidates:
        candidates = pool
    return max(candidates, key=lambda item: (item.duration >= needed + 0.12, -item.index))


def build_plan(storyboard: dict[str, Any], media: list[MediaItem], peaks: list[float], min_shot: float, max_shot: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    used_files: set[Path] = set()
    used_groups: set[int] = set()
    plan_beats: list[dict[str, Any]] = []
    alignment: list[dict[str, Any]] = []
    segment_serial = 1
    for beat in storyboard["beats"]:
        beat_start = float(beat["timeline_start"])
        duration = float(beat["duration"])
        count = shot_count(duration, min_shot, max_shot, str(beat["type"]))
        boundaries = choose_boundaries(beat_start, duration, peaks, count, min_shot)
        pool = pool_for_intent(media, str(beat["shot_intent"]))
        selected_segments: list[dict[str, Any]] = []
        cut_times: list[float] = []
        for shot_index, (a, b) in enumerate(zip(boundaries, boundaries[1:]), start=1):
            shot_duration = round(b - a, 3)
            if shot_duration <= 0:
                continue
            item = select_media(pool, used_files, used_groups, shot_duration)
            used_files.add(item.path)
            used_groups.add(item.group_id)
            use_start = 0.15 if item.duration - shot_duration > 0.25 else 0.0
            selected_segments.append(
                {
                    "segment_id": f"segment_{segment_serial:04d}",
                    "video_path": str(item.path),
                    "source_duration": round(item.duration, 3),
                    "use_start": round(use_start, 3),
                    "use_duration": shot_duration,
                    "selection_reason": f"{beat['shot_intent']} shot {shot_index}: {beat['visual_action']}",
                    "audio_peak_cut": round(a, 3),
                    "visual_group_id": item.group_id,
                }
            )
            cut_times.append(round(a, 3))
            segment_serial += 1
        plan_beats.append(
            {
                "beat_id": f"beat_{int(beat['id']):04d}",
                "beat_type": beat["type"],
                "script_text": beat["voiceover"],
                "visual_goal": beat["visual_action"],
                "shot_note": beat["notes"] + " Multi-shot cut: visual must stay within this voiceover meaning.",
                "timeline_start": beat_start,
                "timeline_duration": duration,
                "selected_segments": selected_segments,
                "alternatives": [],
                "overlay_style": "pov_top_caption",
            }
        )
        alignment.append(
            {
                "beat_id": int(beat["id"]),
                "voiceover": beat["voiceover"],
                "shot_intent": beat["shot_intent"],
                "beat_start": beat_start,
                "duration": duration,
                "shot_count": len(selected_segments),
                "cut_times": cut_times,
                "selected_files": [Path(seg["video_path"]).name for seg in selected_segments],
                "visual_group_ids": [seg["visual_group_id"] for seg in selected_segments],
            }
        )
    plan = {
        "project_name": storyboard["project_name"] + "_peak_matched",
        "capcut_ratio": storyboard["aspect_ratio"],
        "style_preset": "capcut_native_fast_pov_peak_matched",
        "audio_peak_policy": "segment boundaries are placed on or near local voiceover energy peaks",
        "beats": plan_beats,
    }
    return plan, alignment


def write_report(path: Path, alignment: list[dict[str, Any]], peaks: list[float]) -> None:
    lines = [
        "# Shot Peak Alignment Report",
        "",
        f"Detected usable audio peaks: {len(peaks)}",
        "",
        "| Beat | Shots | Cut Times | Files |",
        "|---:|---:|---|---|",
    ]
    for item in alignment:
        lines.append(
            f"| {item['beat_id']} | {item['shot_count']} | {', '.join(f'{t:.3f}s' for t in item['cut_times'])} | {', '.join(item['selected_files'])} |"
        )
    lines.extend(
        [
            "",
            "Rules applied:",
            "- More than one video segment per voiceover beat.",
            "- One source file is used once.",
            "- Perceptually similar source groups are avoided when possible.",
            "- Shot cuts stay inside their matching voiceover beat so the image does not drift away from the narration.",
        ]
    )
    write_text(path, "\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    media_dir = Path(args.media_dir)
    output_dir = Path(args.output_dir)
    storyboard = read_json(Path(args.storyboard))
    media = scan_media(media_dir, args.max_videos)
    if not media:
        raise ValueError(f"No video files found under {media_dir}")
    peaks = local_peak_times(Path(args.voiceover_wav))
    if args.bgm_path:
        # Add some BGM transient candidates, but keep voiceover as the primary timing source.
        peaks = sorted(set(peaks + local_peak_times(Path(args.bgm_path))[::2]))
    plan, alignment = build_plan(storyboard, media, peaks, args.min_shot_duration, args.max_shot_duration)
    plan_path = output_dir / args.draft_plan_out
    write_json(plan_path, plan)
    write_json(output_dir / "shot_peak_alignment.json", alignment)
    write_report(output_dir / "shot_peak_alignment_report.md", alignment, peaks)
    print(json.dumps({"plan": str(plan_path), "beats": len(plan["beats"]), "segments": sum(len(b["selected_segments"]) for b in plan["beats"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
