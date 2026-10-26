#!/usr/bin/env python3
"""Split a storyboard grid into row-banded segment images.

Example:
  python split_storyboard.py input.jpg out_dir --prefix video1 --rows 6 --cols 2 --rows-per-segment 2
  python split_storyboard.py input.jpg out_dir --prefix video1 --rows 4 --cols 4 --row-groups 1-2,3,4
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_row_groups(value: str, rows: int) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s)
            end = int(end_s)
        else:
            start = end = int(part)
        if start < 1 or end < start or end > rows:
            raise SystemExit(f"invalid row group {part!r} for {rows} rows")
        groups.append((start - 1, end))
    if not groups:
        raise SystemExit("row-groups did not contain any groups")
    return groups


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--prefix", default="segment")
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, default=2)
    parser.add_argument("--rows-per-segment", type=int, default=2)
    parser.add_argument("--row-groups", help="1-based row groups, e.g. 1-2,3,4")
    parser.add_argument("--quality", type=int, default=95)
    args = parser.parse_args()

    if args.rows <= 0 or args.cols <= 0 or args.rows_per_segment <= 0:
        raise SystemExit("rows, cols, and rows-per-segment must be positive")

    image = Image.open(args.input)
    width, height = image.size
    row_h = height / args.rows
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.row_groups:
        row_groups = parse_row_groups(args.row_groups, args.rows)
    else:
        row_groups = []
        start_row = 0
        while start_row < args.rows:
            end_row = min(start_row + args.rows_per_segment, args.rows)
            row_groups.append((start_row, end_row))
            start_row = end_row

    for segment_index, (start_row, end_row) in enumerate(row_groups, start=1):
        top = round(start_row * row_h)
        bottom = round(end_row * row_h)
        crop = image.crop((0, top, width, bottom))
        out = args.output_dir / f"{args.prefix}_segment_{segment_index:02d}.jpg"
        crop.save(out, quality=args.quality)
        print(out)


if __name__ == "__main__":
    main()
