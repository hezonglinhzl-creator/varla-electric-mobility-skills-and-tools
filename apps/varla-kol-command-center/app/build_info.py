"""Public, path-free build identity for safe launcher reuse."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


BUILD_ID = "varla-kol-command-center/2026.08.04.2"
_INSTANCE_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def project_instance_id(project_root: str | Path) -> str:
    """Return a stable hash for one checkout without exposing its path."""
    injected = os.environ.get("VARLA_KOL_INSTANCE_ID", "").strip().lower()
    if _INSTANCE_PATTERN.fullmatch(injected):
        return injected
    normalized = str(Path(project_root).resolve()).rstrip("\\/").casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["BUILD_ID", "project_instance_id"]
