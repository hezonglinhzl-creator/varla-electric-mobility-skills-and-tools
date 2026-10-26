"""Allowlisted local file entry points for the command center."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from app.config import AppConfig


LOCAL_TARGETS = frozenset({"database", "reply", "contract"})


def resolve_local_target(config: AppConfig, target: str) -> tuple[Path, bool]:
    """Return one preconfigured path and whether Explorer should select it."""

    if target == "database":
        return config.data_dir / "command-center.sqlite3", True
    if target == "reply":
        return (
            Path.home() / ".codex" / "skills" / "varla-kol-reply-assistant",
            False,
        )
    if target == "contract":
        return (
            Path.home() / ".codex" / "skills" / "varla-kol-contract-updater",
            False,
        )
    raise ValueError("unsupported service target")


def open_local_target(
    config: AppConfig,
    target: str,
    *,
    launcher: Callable[..., object] = subprocess.Popen,
) -> dict[str, str]:
    """Open one allowlisted path without accepting caller-supplied paths."""

    path, select_file = resolve_local_target(config, target)
    resolved = path.resolve(strict=True)
    if select_file and not resolved.is_file():
        raise FileNotFoundError("configured database file is unavailable")
    if not select_file and not resolved.is_dir():
        raise FileNotFoundError("configured skill directory is unavailable")

    command = (
        ["explorer.exe", f"/select,{resolved}"]
        if select_file
        else ["explorer.exe", str(resolved)]
    )
    launcher(
        command,
        close_fds=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"status": "opened", "target": target}


__all__ = ["LOCAL_TARGETS", "open_local_target", "resolve_local_target"]
