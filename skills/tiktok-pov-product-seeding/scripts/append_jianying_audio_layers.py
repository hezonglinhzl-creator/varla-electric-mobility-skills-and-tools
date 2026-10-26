from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any


def uid() -> str:
    return str(uuid.uuid4()).upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append BGM/SFX audio layers to a plaintext Jianying/CapCut draft while preserving existing voiceover.")
    parser.add_argument("--draft-dir", required=True)
    parser.add_argument("--bgm-path", required=True)
    parser.add_argument("--bgm-volume", type=float, default=0.22)
    parser.add_argument("--sfx-events", help="Optional JSON list with path/start/duration/volume entries.")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    if not raw.lstrip().startswith(b"{"):
        raise ValueError(f"{path} is not plaintext JSON. Create a new draft instead of patching an encrypted/open draft.")
    return json.loads(raw.decode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def norm(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def us(seconds: float) -> int:
    return int(round(float(seconds) * 1_000_000))


def media_duration_us(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()
    return us(float(out))


def project_duration(payload: dict[str, Any]) -> int:
    if int(payload.get("duration") or 0) > 0:
        return int(payload["duration"])
    end = 0
    for track in payload.get("tracks", []):
        for segment in track.get("segments", []):
            timerange = segment.get("target_timerange") or {}
            end = max(end, int(timerange.get("start") or 0) + int(timerange.get("duration") or 0))
    return end


def make_speed() -> dict[str, Any]:
    return {"curve_speed": None, "id": uid(), "mode": 0, "speed": 1.0, "type": "speed"}


def make_audio_material(path: Path, duration_us: int, name: str) -> dict[str, Any]:
    material_id = uid()
    return {
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 3,
        "copyright_limit_type": "none",
        "duration": duration_us,
        "effect_id": "",
        "formula_id": "",
        "id": material_id,
        "local_material_id": material_id,
        "music_id": material_id,
        "name": name,
        "path": norm(path),
        "source_platform": 0,
        "type": "extract_music",
        "wave_points": [],
    }


def make_audio_segment(material_id: str, speed_id: str, start_us: int, duration_us: int, volume: float, render_index: int) -> dict[str, Any]:
    return {
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "last_nonzero_volume": volume,
        "reverse": False,
        "track_attribute": 0,
        "track_render_index": 0,
        "visible": True,
        "id": uid(),
        "material_id": material_id,
        "target_timerange": {"start": start_us, "duration": duration_us},
        "common_keyframes": [],
        "keyframe_refs": [],
        "source_timerange": {"start": 0, "duration": duration_us},
        "speed": 1,
        "volume": volume,
        "extra_material_refs": [speed_id],
        "is_tone_modify": False,
        "clip": None,
        "hdr_settings": None,
        "render_index": render_index,
    }


def make_track(name: str, kind: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {"attribute": 0, "flag": 0, "id": uid(), "is_default_name": False, "name": name, "segments": segments, "type": kind}


def patch_payload(payload: dict[str, Any], bgm_path: Path, bgm_volume: float, sfx_events_path: Path | None) -> dict[str, Any]:
    materials = payload.setdefault("materials", {})
    audios = materials.setdefault("audios", [])
    speeds = materials.setdefault("speeds", [])
    tracks = payload.setdefault("tracks", [])
    duration = project_duration(payload)
    payload["duration"] = duration

    tracks[:] = [track for track in tracks if track.get("name") not in {"bgm_main", "sfx_event"}]

    bgm_duration = min(duration, media_duration_us(bgm_path))
    bgm_speed = make_speed()
    bgm_material = make_audio_material(bgm_path, bgm_duration, "BGM_" + bgm_path.name)
    speeds.append(bgm_speed)
    audios.append(bgm_material)
    tracks.append(make_track("bgm_main", "audio", [make_audio_segment(bgm_material["id"], bgm_speed["id"], 0, bgm_duration, bgm_volume, 2000)]))

    if sfx_events_path and sfx_events_path.exists():
        events = read_json(sfx_events_path)
        sfx_segments: list[dict[str, Any]] = []
        for index, event in enumerate(events):
            path_value = event.get("path")
            if not path_value:
                continue
            path = Path(path_value)
            if not path.exists():
                continue
            start = us(float(event.get("start", 0.0)))
            event_duration = min(us(float(event.get("duration", 0.7))), max(duration - start, 0), media_duration_us(path))
            if event_duration <= 0:
                continue
            speed = make_speed()
            material = make_audio_material(path, event_duration, str(event.get("name") or path.name))
            speeds.append(speed)
            audios.append(material)
            sfx_segments.append(make_audio_segment(material["id"], speed["id"], start, event_duration, float(event.get("volume", 0.8)), 3000 + index))
        if sfx_segments:
            tracks.append(make_track("sfx_event", "audio", sfx_segments))

    return payload


def main() -> None:
    args = parse_args()
    draft_dir = Path(args.draft_dir).resolve()
    bgm_path = Path(args.bgm_path).resolve()
    sfx_events_path = Path(args.sfx_events).resolve() if args.sfx_events else None
    for filename in ("draft_content.json", "draft_info.json"):
        path = draft_dir / filename
        payload = read_json(path)
        write_json(path, patch_payload(payload, bgm_path, args.bgm_volume, sfx_events_path))
        print(path)


if __name__ == "__main__":
    main()
