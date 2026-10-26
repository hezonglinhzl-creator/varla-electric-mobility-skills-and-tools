"""Resolve the single Python runtime used by local child processes."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def resolve_runtime(explicit: str | Path | None = None) -> Path:
    configured = explicit or os.environ.get("VARLA_KOL_PYTHON") or sys.executable
    candidate = Path(configured).expanduser()
    if not candidate.is_file():
        raise RuntimeError("configured command-center Python runtime is unavailable")
    # Keep the selected virtual-environment launcher.  Resolving a Windows
    # venv executable can collapse it to the base interpreter, which loses the
    # venv's installed Gmail dependencies for child health checks.
    return candidate.absolute()


__all__ = ["resolve_runtime"]
