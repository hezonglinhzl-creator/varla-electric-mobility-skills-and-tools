#!/usr/bin/env python3
"""Dry-run first wrapper for Dreamina/Jimeng image-to-video jobs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_job(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("job file must contain a JSON object")
    return data


def add_if_value(command: list[str], flag: str, value: Any) -> None:
    if value is None or value == "":
        return
    command.append(flag)
    command.append(str(value))


def build_command(args: argparse.Namespace, job: dict[str, Any]) -> tuple[list[str], list[str]]:
    dreamina = shutil.which(args.dreamina_bin)
    warnings: list[str] = []
    if not dreamina:
        dreamina = args.dreamina_bin
        warnings.append(f"Dreamina CLI not found on PATH: {args.dreamina_bin}")

    image = Path(args.image or job.get("image") or "").expanduser()
    if not image:
        raise ValueError("missing --image or job.image")
    if not image.exists():
        raise FileNotFoundError(f"image not found: {image}")

    prompt = args.prompt or job.get("prompt")
    prompt_file = args.prompt_file or job.get("prompt_file")
    if not prompt and prompt_file:
        prompt = read_text(Path(prompt_file).expanduser())
    if not prompt:
        raise ValueError("missing --prompt, --prompt-file, job.prompt, or job.prompt_file")

    command = [dreamina, "image2video", "--image", str(image), "--prompt", prompt]
    add_if_value(command, "--duration", args.duration or job.get("duration"))
    add_if_value(command, "--poll", args.poll if args.poll is not None else job.get("poll"))
    add_if_value(command, "--model_version", args.model_version or job.get("model_version"))
    add_if_value(command, "--video_resolution", args.video_resolution or job.get("video_resolution"))
    add_if_value(command, "--ratio", args.ratio or job.get("ratio"))

    return command, warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or submit a Dreamina/Jimeng image2video task."
    )
    parser.add_argument("--job", help="UTF-8 JSON job file from GPT prompt review")
    parser.add_argument("--image", help="Source image path")
    parser.add_argument("--prompt", help="Final English motion prompt")
    parser.add_argument("--prompt-file", help="Text file containing final prompt")
    parser.add_argument("--duration", type=int, help="Video duration in seconds")
    parser.add_argument("--poll", type=int, default=None, help="Polling interval/seconds")
    parser.add_argument("--ratio", help="Optional ratio if supported by installed CLI")
    parser.add_argument("--model-version", help="Optional Dreamina model version")
    parser.add_argument("--video-resolution", help="Optional video resolution, for example 720p")
    parser.add_argument("--dreamina-bin", default="dreamina", help="Dreamina CLI executable")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually submit the task. Without this flag the script only dry-runs.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    job = load_job(Path(args.job).expanduser()) if args.job else {}

    try:
        command, warnings = build_command(args, job)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    if not args.execute:
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "dry_run",
                    "will_consume_credits": False,
                    "command": command,
                    "warnings": warnings,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if warnings:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "preflight failed",
                    "warnings": warnings,
                    "command": command,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3

    completed = subprocess.run(command, text=True, capture_output=True)
    payload: dict[str, Any] = {
        "ok": completed.returncode == 0,
        "mode": "execute",
        "returncode": completed.returncode,
        "command": command,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
