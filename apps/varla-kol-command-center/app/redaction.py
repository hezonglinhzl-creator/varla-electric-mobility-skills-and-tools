"""Defensive recursive redaction for JSON-bound persistence data."""

from __future__ import annotations

import re
from typing import Any


REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PATTERNS = frozenset(
    {
        "access_token",
        "refresh_token",
        "oauth_token",
        "token",
        "api_key",
        "access_key",
        "client_secret",
        "app_secret",
        "signing_secret",
        "webhook_secret",
        "feishu_app_secret",
        "secret",
        "password",
        "client_password",
        "credentials",
        "authorization",
        "private_key",
    }
)

# These are operational settings, not authentication material.
_SAFE_NORMALIZED_KEYS = frozenset({"password_policy", "token_budget"})
_SAFE_NORMALIZED_SUFFIXES = (
    "_password_policy",
    "_token_budget",
    "_credentials_path",
    "_token_path",
)


def _normalize_key(key: str) -> str:
    snake_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-z0-9]+", "_", snake_case.lower()).strip("_")


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _SAFE_NORMALIZED_KEYS or normalized.endswith(
        _SAFE_NORMALIZED_SUFFIXES
    ):
        return False

    padded = f"_{normalized}_"
    return any(
        normalized == pattern or f"_{pattern}_" in padded
        for pattern in _SENSITIVE_KEY_PATTERNS
    )


def redact_sensitive_json(value: Any) -> Any:
    """Return a detached JSON-like structure with secret values redacted."""
    if isinstance(value, dict):
        return {
            key: (
                REDACTED
                if isinstance(key, str) and _is_sensitive_key(key)
                else redact_sensitive_json(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_json(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive_json(item) for item in value]
    return value
