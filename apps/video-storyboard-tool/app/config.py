"""Configuration loading for local processing and Feishu credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "outputs"
STATIC_DIR = ROOT_DIR / "static"
LOCAL_FEISHU_CONFIG = Path.home() / ".feishu-docs" / "config.json"

load_dotenv(ROOT_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_feishu_config() -> dict[str, str]:
    """Read .env first, then fall back to the existing local Feishu tool config."""
    config: dict[str, str] = {}
    if LOCAL_FEISHU_CONFIG.exists():
        try:
            raw = json.loads(LOCAL_FEISHU_CONFIG.read_text(encoding="utf-8"))
            config.update(
                {
                    "app_id": raw.get("app_id", ""),
                    "app_secret": raw.get("app_secret", ""),
                    "folder_token": raw.get("default_folder_token", ""),
                }
            )
        except Exception:
            pass

    env_map = {
        "app_id": "FEISHU_APP_ID",
        "app_secret": "FEISHU_APP_SECRET",
        "user_access_token": "FEISHU_USER_ACCESS_TOKEN",
        "bitable_app_token": "FEISHU_BITABLE_APP_TOKEN",
        "bitable_table_id": "FEISHU_BITABLE_TABLE_ID",
        "bitable_url": "FEISHU_BITABLE_URL",
        "folder_token": "FEISHU_FOLDER_TOKEN",
        "doc_folder_token": "FEISHU_DOC_FOLDER_TOKEN",
        "doc_url": "FEISHU_DOC_URL",
        "doc_id": "FEISHU_DOC_ID",
        "wiki_parent_node_token": "FEISHU_WIKI_PARENT_NODE_TOKEN",
        "wiki_parent_url": "FEISHU_WIKI_PARENT_URL",
        "default_sync_target": "FEISHU_DEFAULT_SYNC_TARGET",
    }
    for key, env_name in env_map.items():
        value = os.getenv(env_name)
        if value:
            config[key] = value
    config["enable_sync"] = "true" if env_bool("FEISHU_ENABLE_SYNC", True) else "false"
    return config


def get_processing_settings() -> dict[str, str | float]:
    return {
        "whisper_model": os.getenv("WHISPER_MODEL", "tiny"),
        "scene_threshold": float(os.getenv("SCENE_THRESHOLD", "27.0")),
        "min_shot_seconds": float(os.getenv("MIN_SHOT_SECONDS", "0.6")),
    }
