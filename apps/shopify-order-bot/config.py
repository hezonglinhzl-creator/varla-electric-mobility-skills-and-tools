from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PLACEHOLDER_ADMIN_URL = "https://your-store.myshopify.com/admin"


def _load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


BASE_DIR = Path(__file__).resolve().parent
_load_local_env(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime configuration kept separate from browser behavior."""

    base_dir: Path = BASE_DIR
    shopify_admin_url: str = os.getenv("SHOPIFY_ADMIN_URL", PLACEHOLDER_ADMIN_URL)
    adspower_api_url: str = os.getenv(
        "ADSPOWER_API_URL",
        "http://local.adspower.net:50325",
    )
    adspower_api_key: str = os.getenv("ADSPOWER_API_KEY", "")
    adspower_profile_id: str = os.getenv("ADSPOWER_PROFILE_ID", "")
    google_maps_url: str = "https://www.google.com/maps"
    default_timeout_ms: int = 20_000
    maps_result_timeout_ms: int = 15_000
    adspower_api_timeout_seconds: float = 20.0

    @property
    def excel_path(self) -> Path:
        return self.base_dir / "KOL_order.xlsx"

    @property
    def profile_dir(self) -> Path:
        return self.base_dir / "browser_profile"

    @property
    def log_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def debug_screenshot_path(self) -> Path:
        return self.base_dir / "debug_screenshot.png"

    def ensure_runtime_dirs(self) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def validate_admin_url(self) -> None:
        url = self.shopify_admin_url.strip()
        if not url or url == PLACEHOLDER_ADMIN_URL or "your-store" in url:
            raise ValueError(
                "请先在 config.py 修改 SHOPIFY_ADMIN_URL，"
                "或设置环境变量 SHOPIFY_ADMIN_URL。"
            )
        if not url.startswith(("https://", "http://")):
            raise ValueError("SHOPIFY_ADMIN_URL 必须以 https:// 或 http:// 开头")
        if "/admin" not in url:
            raise ValueError("SHOPIFY_ADMIN_URL 必须包含 /admin")

    def validate_adspower(self) -> None:
        if not self.adspower_api_url.startswith(("http://", "https://")):
            raise ValueError("ADSPOWER_API_URL 必须是有效的本地 HTTP 地址")
        if not self.adspower_api_key:
            raise ValueError("请在本地 .env 配置 ADSPOWER_API_KEY")


def configure_logging(settings: Settings) -> tuple[logging.Logger, Path]:
    settings.ensure_runtime_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = settings.log_dir / f"run_{timestamp}.log"
    logger = logging.getLogger("shopify_order_bot")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger, log_path


SETTINGS = Settings()
