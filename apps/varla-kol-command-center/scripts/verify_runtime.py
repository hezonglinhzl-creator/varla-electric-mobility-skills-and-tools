"""Fail-closed verification for the launcher-managed Python runtime."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_IMPORTS = (
    "fastapi",
    "uvicorn",
    "pydantic",
    "docx",
    "httpx",
    "app.main",
)
_PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def locked_versions(path: Path) -> dict[str, tuple[str, str]]:
    pins: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _PIN.match(line)
        if match:
            distribution, version = match.groups()
            pins[canonical_name(distribution)] = (distribution, version)
    if not pins:
        raise RuntimeError("requirements.lock contains no exact pins")
    return pins


def verify(lock_path: Path, project_root: Path) -> None:
    if not lock_path.is_file():
        raise RuntimeError("requirements.lock is missing")
    root = str(project_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    for module in REQUIRED_IMPORTS:
        importlib.import_module(module)

    for canonical, (distribution, expected) in locked_versions(lock_path).items():
        del canonical
        actual = importlib.metadata.version(distribution)
        if actual != expected:
            raise RuntimeError(
                f"locked dependency version mismatch: {distribution}"
            )

    check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )
    if check.returncode != 0:
        raise RuntimeError("pip dependency check failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        verify(args.lock, args.project_root)
    except (
        ImportError,
        importlib.metadata.PackageNotFoundError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        UnicodeError,
    ) as exc:
        print(f"RUNTIME_INVALID: {exc}", file=sys.stderr)
        return 1
    print("RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
