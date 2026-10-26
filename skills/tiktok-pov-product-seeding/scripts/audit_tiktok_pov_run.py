from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a TikTok POV automation run before sending it to Jianying.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--plan-file", help="Retrieval plan JSON to audit.")
    parser.add_argument("--draft-dir", help="Optional plaintext Jianying/CapCut draft directory.")
    parser.add_argument("--voice-manifest", help="Optional voiceover_manifest.json path.")
    parser.add_argument("--report-out", default="automation_audit_report.md")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    if not raw.lstrip().startswith((b"{", b"[")):
        raise ValueError(f"{path} is not plaintext JSON")
    return json.loads(raw.decode("utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe_video(path: Path) -> dict[str, Any]:
    payload = json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:stream_side_data=rotation",
                "-of",
                "json",
                str(path),
            ]
        ).stdout
    )
    stream = (payload.get("streams") or [{}])[0]
    rotation = 0
    for side_data in stream.get("side_data_list") or []:
        if "rotation" in side_data:
            rotation = int(float(side_data["rotation"]))
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    effective_width, effective_height = (height, width) if abs(rotation) in {90, 270} else (width, height)
    return {
        "width": width,
        "height": height,
        "rotation": rotation,
        "effective_width": effective_width,
        "effective_height": effective_height,
    }


def load_plan(path: Path | None, output_dir: Path) -> dict[str, Any] | None:
    candidates = [
        path,
        output_dir / "jianying_draft" / "retrieval_plan.semantic_peakcut.generated.json",
        output_dir / "jianying_draft" / "retrieval_plan.peak_matched.generated.json",
        output_dir / "jianying_draft" / "retrieval_plan.generated.json",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return read_json(candidate)
    return None


def audio_duration(path: Path) -> float | None:
    if not path.exists():
        return None
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).stdout.strip()
    return float(out) if out else None


def audit_voice(output_dir: Path, voice_manifest_path: Path | None) -> list[str]:
    issues: list[str] = []
    manifest_path = voice_manifest_path or output_dir / "voiceover_manifest.json"
    if not manifest_path.exists():
        return ["FAIL: missing voiceover_manifest.json, cannot prove script and voice are aligned."]
    manifest = read_json(manifest_path)
    mode = str(manifest.get("mode") or "")
    voice = str(manifest.get("voice") or manifest.get("voice_name") or "")
    if "copied_existing_voiceover_or_reference" in mode or "retimed_existing_voiceover" in mode:
        issues.append("FAIL: voiceover was copied/retimed from an existing file. If script changed, regenerate CosyVoice first.")
    if voice and voice.lower() != "ryan" and "cosyvoice" in str(manifest.get("engine", "")).lower():
        issues.append(f"WARN: CosyVoice voice is `{voice}`, expected `ryan` for this run.")
    voice_path = Path(str(manifest.get("wav") or manifest.get("voiceover_wav") or output_dir / "voiceover.wav"))
    duration = audio_duration(voice_path) if voice_path.exists() else None
    if duration is None:
        issues.append(f"FAIL: voiceover audio is missing or unreadable: {voice_path}")
    elif duration < 8:
        issues.append(f"FAIL: voiceover duration looks too short: {duration:.2f}s")
    return issues


def audit_plan(plan: dict[str, Any] | None) -> list[str]:
    if plan is None:
        return ["FAIL: no retrieval plan found, cannot audit shot-to-copy alignment."]
    issues: list[str] = []
    used_files: set[str] = set()
    all_segments: list[dict[str, Any]] = []
    for beat in plan.get("beats", []):
        beat_type = str(beat.get("beat_type") or beat.get("type") or "")
        segments = beat.get("selected_segments") or []
        files = [str(Path(str(seg.get("video_path", ""))).name) for seg in segments]
        distinct_files = sorted(set(files))
        if beat_type == "power_on" and len(distinct_files) > 1:
            issues.append(
                "FAIL: power_on beat uses multiple different files. Use one complete key/power action only; cuts inside one file are OK."
            )
        for seg in segments:
            video_path = str(seg.get("video_path", "")).strip()
            if not video_path:
                issues.append(f"FAIL: {beat.get('beat_id')} has a selected segment without video_path.")
                continue
            if video_path in used_files:
                issues.append(f"WARN: source file reused: {Path(video_path).name}. Reuse only when it is one intentional cut inside one action.")
            used_files.add(video_path)
            seg["_beat_type"] = beat_type
            all_segments.append(seg)
    for seg in all_segments:
        path = Path(str(seg.get("video_path", "")))
        if not path.exists():
            issues.append(f"FAIL: selected source missing: {path}")
            continue
        try:
            info = probe_video(path)
        except Exception as exc:
            issues.append(f"WARN: could not probe video {path.name}: {exc}")
            continue
        ew = info["effective_width"]
        eh = info["effective_height"]
        ratio = ew / eh if eh else 0
        if not (0.54 <= ratio <= 0.60):
            issues.append(f"FAIL: {path.name} is not effective 9:16 after rotation ({ew}x{eh}). Reject or crop before draft.")
        if info["width"] > info["height"] and abs(info["rotation"]) in {90, 270}:
            issues.append(f"CHECK: {path.name} is phone-vertical via rotation metadata. Jianying draft must fill 9:16, not use raw landscape bounds.")
    return issues


def audit_draft(draft_dir: Path | None) -> list[str]:
    if not draft_dir:
        return []
    content_path = draft_dir / "draft_content.json"
    if not content_path.exists():
        return [f"FAIL: draft_content.json not found in {draft_dir}"]
    try:
        payload = read_json(content_path)
    except Exception as exc:
        return [f"WARN: cannot audit draft JSON directly: {exc}. Create or inspect a plaintext draft copy before delivery."]
    tracks = payload.get("tracks") or []
    audio_track_names = [str(track.get("name") or "") for track in tracks if track.get("type") == "audio"]
    if not any("voice" in name.lower() for name in audio_track_names):
        return_issues = ["WARN: no explicitly named voice audio track found; verify narration did not merge with BGM."]
    else:
        return_issues = []
    if "bgm_main" not in audio_track_names:
        return_issues.append("FAIL: missing separate `bgm_main` audio track.")
    video_segments = [seg for track in tracks if track.get("type") == "video" for seg in track.get("segments", [])]
    if len(video_segments) < 12:
        return_issues.append(f"WARN: only {len(video_segments)} video segments. TikTok POV version may feel too sparse.")
    for seg in video_segments:
        clip = seg.get("clip") or {}
        if clip.get("rotation", 0) == 0 and (clip.get("scale") or {}).get("x", 1) == 1:
            return_issues.append("CHECK: video segment uses default rotation/scale. Inspect vertical fill in Jianying for black bars.")
            break
    return return_issues


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    plan = load_plan(Path(args.plan_file).resolve() if args.plan_file else None, output_dir)
    draft_dir = Path(args.draft_dir).resolve() if args.draft_dir else None
    voice_manifest = Path(args.voice_manifest).resolve() if args.voice_manifest else None
    issues = []
    issues.extend(audit_voice(output_dir, voice_manifest))
    issues.extend(audit_plan(plan))
    issues.extend(audit_draft(draft_dir))
    fail_count = sum(1 for item in issues if item.startswith("FAIL"))
    warn_count = sum(1 for item in issues if item.startswith("WARN"))
    check_count = sum(1 for item in issues if item.startswith("CHECK"))
    lines = [
        "# Automation Audit Report",
        "",
        f"Status: {'FAIL' if fail_count else 'REVIEW' if warn_count or check_count else 'PASS'}",
        f"Failures: {fail_count}",
        f"Warnings: {warn_count}",
        f"Manual checks: {check_count}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(f"- {item}" for item in issues) if issues else lines.append("- No blocking issues found.")
    report_path = output_dir / args.report_out
    write_text(report_path, "\n".join(lines) + "\n")
    print(report_path)
    print("\n".join(lines))
    raise SystemExit(1 if fail_count else 0)


if __name__ == "__main__":
    main()
