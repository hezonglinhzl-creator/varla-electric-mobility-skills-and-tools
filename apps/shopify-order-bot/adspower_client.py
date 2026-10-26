from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import httpx


class AdsPowerError(RuntimeError):
    """Safe AdsPower error that never includes authorization headers."""


@dataclass(frozen=True)
class AdsPowerProfile:
    profile_id: str
    profile_no: str = ""
    name: str = ""
    group_name: str = ""
    platform: str = ""


@dataclass(frozen=True)
class BrowserStartResult:
    profile_id: str
    websocket_url: str


class AdsPowerClient:
    """Small V2-first, V1-compatible client for the AdsPower Local API."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        timeout_seconds: float = 20.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._owns_http_client = http_client is None
        self._request_interval_seconds = 1.05 if http_client is None else 0.0
        self._last_request_at = 0.0
        headers = {"Authorization": api_key} if api_key else {}
        self.http = http_client or httpx.Client(
            base_url=api_base_url.rstrip("/"),
            headers=headers,
            timeout=timeout_seconds,
            trust_env=False,
        )

    def close(self) -> None:
        if self._owns_http_client:
            self.http.close()

    def __enter__(self) -> "AdsPowerClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _extract_data(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("code") not in (0, "0"):
            raise AdsPowerError(str(payload.get("msg") or "AdsPower 请求失败"))
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise AdsPowerError("AdsPower 返回了无法识别的数据")
        return data

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self._request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            self._throttle()
            response = self.http.get(path, params=params)
            response.raise_for_status()
            return self._extract_data(response.json())
        except AdsPowerError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise AdsPowerError(f"AdsPower 本地服务请求失败: {path}") from exc

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            self._throttle()
            response = self.http.post(path, json=payload)
            response.raise_for_status()
            return self._extract_data(response.json())
        except AdsPowerError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise AdsPowerError(f"AdsPower 本地服务请求失败: {path}") from exc

    def list_profiles(self, limit: int = 100) -> list[AdsPowerProfile]:
        try:
            data = self._post(
                "/api/v2/browser-profile/list",
                {"page": 1, "limit": min(limit, 100)},
            )
            rows = data.get("list", [])
            return [
                AdsPowerProfile(
                    profile_id=str(row.get("profile_id", "")),
                    profile_no=str(row.get("profile_no", "")),
                    name=str(row.get("name", "")),
                    group_name=str(row.get("group_name", "")),
                    platform=str(row.get("platform", "")),
                )
                for row in rows
                if row.get("profile_id")
            ]
        except AdsPowerError:
            data = self._get(
                "/api/v1/user/list",
                {"page": 1, "page_size": min(limit, 100)},
            )
            rows = data.get("list", [])
            return [
                AdsPowerProfile(
                    profile_id=str(row.get("user_id", "")),
                    profile_no=str(row.get("serial_number", "")),
                    name=str(row.get("name", "")),
                    group_name=str(row.get("group_name", "")),
                    platform=str(row.get("domain_name", "")),
                )
                for row in rows
                if row.get("user_id")
            ]

    @staticmethod
    def _parse_start_result(
        profile_id: str,
        data: dict[str, Any],
    ) -> BrowserStartResult:
        websocket_data = data.get("ws") or {}
        websocket_url = websocket_data.get("puppeteer") or data.get("ws_endpoint")
        if not websocket_url:
            raise AdsPowerError("AdsPower 未返回可用的 CDP 地址")
        return BrowserStartResult(
            profile_id=profile_id,
            websocket_url=str(websocket_url),
        )

    def browser_status(self, profile_id: str) -> BrowserStartResult | None:
        try:
            data = self._get(
                "/api/v1/browser/active",
                {"user_id": profile_id},
            )
        except AdsPowerError:
            return None
        websocket_data = data.get("ws") or {}
        websocket_url = websocket_data.get("puppeteer")
        if not websocket_url:
            return None
        return BrowserStartResult(profile_id, str(websocket_url))

    def start_browser(self, profile_id: str) -> BrowserStartResult:
        active = self.browser_status(profile_id)
        if active is not None:
            return active
        try:
            data = self._post(
                "/api/v2/browser-profile/start",
                {
                    "profile_id": profile_id,
                    "last_opened_tabs": "0",
                    "proxy_detection": "0",
                },
            )
        except AdsPowerError:
            data = self._get(
                "/api/v1/browser/start",
                {
                    "user_id": profile_id,
                    "open_tabs": "0",
                    "ip_tab": "0",
                },
            )
        return self._parse_start_result(profile_id, data)

    def stop_browser(self, profile_id: str) -> None:
        """Close one AdsPower browser process without changing its profile data."""

        try:
            self._post(
                "/api/v2/browser-profile/stop",
                {"profile_id": profile_id},
            )
        except AdsPowerError:
            self._get(
                "/api/v1/browser/stop",
                {"user_id": profile_id},
            )
