#!/usr/bin/env python3
"""Validate the structural coverage of an emoto UGC prompt Markdown file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TIME_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[–—-]\s*(\d+(?:\.\d+)?)\s*秒")
SHOT_RE = re.compile(r"镜头\s*[1-9一二三四五六七八九]")


def count_any(text: str, terms: list[str]) -> int:
    return sum(text.count(term) for term in terms)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        text = args.prompt.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot read UTF-8 prompt: {exc}", file=sys.stderr)
        return 2

    ranges = [(float(a), float(b)) for a, b in TIME_RANGE_RE.findall(text)]
    invalid_ranges = [(a, b) for a, b in ranges if b <= a]

    metrics = {
        "time_ranges": len(ranges),
        "shot_markers": len(SHOT_RE.findall(text)),
        "hard_cut_markers": count_any(text, ["硬切", "切到", "反打"]),
        "speaker_lock_markers": count_any(text, ["说话者锁定", "只有", "口型", "不得交换说话者"]),
        "product_reference_markers": count_any(text, ["@M7S", "产品真值", "产品参考图", "VARLA M7S"]),
        "iphone_realism_markers": count_any(text, ["Apple iPhone", "iPhone 后置", "后置主摄1x", "手持"]),
        "facial_markers": count_any(
            text,
            ["眉", "眼睛", "眨眼", "下巴", "嘴角", "脸颊", "视线", "抿嘴", "张嘴"],
        ),
        "micro_action_markers": count_any(
            text,
            ["吞咽", "擦汗", "抓紧", "松开", "捂嘴", "后退", "前倾", "回头", "伸手", "缩回"],
        ),
        "body_reaction_markers": count_any(
            text,
            ["肩膀", "身体", "重心", "弯腰", "拥抱", "张开双臂", "僵住", "后仰"],
        ),
        "camera_continuity_markers": count_any(
            text,
            ["镜头移动", "横移", "跟随", "靠近", "后退拉开", "移动方向", "180度", "人物左右关系"],
        ),
        "replacement_characters": text.count("\ufffd"),
        "invalid_time_ranges": len(invalid_ranges),
    }

    checks = {
        "utf8_clean": metrics["replacement_characters"] == 0,
        "has_timeline": metrics["time_ranges"] >= 3,
        "valid_time_ranges": metrics["invalid_time_ranges"] == 0,
        "has_multiple_shots": metrics["shot_markers"] >= 3 or metrics["hard_cut_markers"] >= 3,
        "has_speaker_lock": metrics["speaker_lock_markers"] >= 3,
        "has_product_lock": metrics["product_reference_markers"] >= 3,
        "has_iphone_realism": metrics["iphone_realism_markers"] >= 2,
        "has_facial_direction": metrics["facial_markers"] >= 5,
        "has_micro_actions": metrics["micro_action_markers"] >= 3,
        "has_body_reactions": metrics["body_reaction_markers"] >= 3,
        "has_camera_continuity": metrics["camera_continuity_markers"] >= 2,
    }

    result = {
        "file": str(args.prompt.resolve()),
        "passed": all(checks.values()),
        "checks": checks,
        "metrics": metrics,
    }

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Prompt: {result['file']}")
        for name, passed in checks.items():
            print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        print("Metrics:")
        for name, value in metrics.items():
            print(f"  {name}: {value}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
