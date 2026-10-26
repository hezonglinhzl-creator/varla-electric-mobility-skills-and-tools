"""Local runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Non-secret settings for the local command center.

    ``project_dir`` is the source checkout root containing ``pyproject.toml``.
    Mutable runtime data belongs under ``data_dir``, never under that source root.
    """

    project_dir: Path
    data_dir: Path
    bind_host: str = "127.0.0.1"
    bind_port: int = 8791
    feishu_check_hours: int = 72
    auto_mode: bool = False
    expected_gmail_account: str = "info@varlascooter.com"
    reply_project_root: Path = Path(
        "E:/himiway/KOL回复训练/脚本/varla-kol-reply-assistant"
    )

    @classmethod
    def from_environment(cls) -> AppConfig:
        """Build the default configuration from the Windows local data root."""
        local_app_data_value = os.environ.get("LOCALAPPDATA")
        if not local_app_data_value:
            raise RuntimeError(
                "LOCALAPPDATA is not set; cannot determine the Varla KOL "
                "Command Center runtime data directory."
            )

        # app/config.py is one directory below the local application's source root.
        project_dir = Path(__file__).resolve().parents[1]
        return cls(
            project_dir=project_dir,
            data_dir=Path(local_app_data_value) / "VarlaKOLCommandCenter",
        )

    def ensure_runtime_dirs(self) -> None:
        """Create the runtime directories owned by this application."""
        for directory_name in ("knowledge-cache", "logs", "backups"):
            (self.data_dir / directory_name).mkdir(parents=True, exist_ok=True)
