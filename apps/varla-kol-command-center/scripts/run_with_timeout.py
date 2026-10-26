"""Run one argument-array command with a hard wall-clock timeout."""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, required=True)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if args.timeout < 1 or not command:
        parser.error("a positive timeout and command are required")
    try:
        completed = subprocess.run(
            command,
            timeout=args.timeout,
            check=False,
            stdout=subprocess.DEVNULL if args.quiet else None,
            stderr=subprocess.DEVNULL if args.quiet else None,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Command timed out after {args.timeout} seconds.",
            file=sys.stderr,
        )
        return 124
    except OSError as exc:
        print(f"Command could not start: {exc}", file=sys.stderr)
        return 125
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
