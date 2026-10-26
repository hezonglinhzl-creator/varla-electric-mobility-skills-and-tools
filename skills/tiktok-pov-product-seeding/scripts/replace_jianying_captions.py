from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any


def uid() -> str:
    return str(uuid.uuid4()).upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replace editable Jianying/CapCut text captions from subtitle_segments.json.")
    parser.add_argument("--draft-dir", required=True)
    parser.add_argument("--subtitle-segments", required=True)
    parser.add_argument("--track-name", default="subtitles")
    parser.add_argument("--font-size", type=float, default=8.2)
    parser.add_argument("--x", type=float, default=0.0)
    parser.add_argument("--y", type=float, default=-0.58)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    raw = path.read_bytes()
    if not raw.lstrip().startswith((b"{", b"[")):
        raise ValueError(f"{path} is not plaintext JSON. Create a new draft instead of patching an encrypted/open draft.")
    return json.loads(raw.decode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def us(seconds: float) -> int:
    return int(round(float(seconds) * 1_000_000))


def text_range(text: str) -> list[int]:
    return [0, len(text.encode("utf-16-le"))]


def make_text_material(text: str, size: float) -> dict[str, Any]:
    material_id = uid()
    content = {
        "styles": [
            {
                "fill": {"alpha": 1.0, "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": [1.0, 0.86, 0.18]}}},
                "range": text_range(text),
                "size": size,
                "bold": True,
                "italic": False,
                "underline": False,
                "strokes": [
                    {"content": {"solid": {"alpha": 1.0, "color": [0.05, 0.04, 0.03]}}, "width": 0.14},
                    {"content": {"solid": {"alpha": 1.0, "color": [1.0, 1.0, 1.0]}}, "width": 0.035},
                ],
            }
        ],
        "text": text,
    }
    return {
        "id": material_id,
        "content": json.dumps(content, ensure_ascii=False),
        "typesetting": 0,
        "alignment": 1,
        "letter_spacing": 0.0,
        "line_spacing": 0.02,
        "line_feed": 1,
        "line_max_width": 0.86,
        "force_apply_line_max_width": False,
        "check_flag": 15,
        "type": "subtitle",
        "global_alpha": 1.0,
    }


def make_text_segment(material_id: str, start_us: int, duration_us: int, x: float, y: float, render_index: int) -> dict[str, Any]:
    return {
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "last_nonzero_volume": 1.0,
        "reverse": False,
        "track_attribute": 0,
        "track_render_index": 0,
        "visible": True,
        "id": uid(),
        "material_id": material_id,
        "target_timerange": {"start": start_us, "duration": duration_us},
        "common_keyframes": [],
        "keyframe_refs": [],
        "source_timerange": None,
        "speed": 1.0,
        "volume": 1.0,
        "extra_material_refs": [],
        "is_tone_modify": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": x, "y": y},
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "render_index": render_index,
    }


def make_track(name: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {"attribute": 0, "flag": 0, "id": uid(), "is_default_name": False, "name": name, "segments": segments, "type": "text"}


def patch_payload(payload: dict[str, Any], cues: list[dict[str, Any]], track_name: str, size: float, x: float, y: float) -> dict[str, Any]:
    materials = payload.setdefault("materials", {})
    text_materials: list[dict[str, Any]] = []
    text_segments: list[dict[str, Any]] = []
    for index, cue in enumerate(cues):
        text = str(cue.get("text", "")).strip()
        if not text:
            continue
        start = us(float(cue["start"]))
        duration = max(us(float(cue.get("duration") or (float(cue["end"]) - float(cue["start"])))), 120_000)
        material = make_text_material(text, size)
        text_materials.append(material)
        text_segments.append(make_text_segment(material["id"], start, duration, x, y, 15000 + index))

    materials["texts"] = text_materials
    tracks = payload.setdefault("tracks", [])
    tracks[:] = [track for track in tracks if track.get("type") != "text" and track.get("name") != track_name]
    tracks.append(make_track(track_name, text_segments))
    return payload


def main() -> None:
    args = parse_args()
    draft_dir = Path(args.draft_dir).resolve()
    cues = read_json(Path(args.subtitle_segments).resolve())
    for filename in ("draft_content.json", "draft_info.json"):
        path = draft_dir / filename
        payload = read_json(path)
        write_json(path, patch_payload(payload, cues, args.track_name, args.font_size, args.x, args.y))
        print(path)


if __name__ == "__main__":
    main()
