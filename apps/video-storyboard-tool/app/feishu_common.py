"""Shared Feishu OpenAPI helpers."""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import urlparse

import requests

from .config import load_feishu_config


API_BASE = "https://open.feishu.cn/open-apis"


class FeishuApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        request_url: str = "",
        http_status: int | str = "",
        code: int | str = "",
        msg: str = "",
        log_id: str = "",
        raw_error: Any = None,
    ) -> None:
        super().__init__(message)
        self.request_url = request_url
        self.http_status = http_status
        self.code = code
        self.msg = msg
        self.log_id = log_id
        self.raw_error = raw_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "request_url": self.request_url,
            "http_status": self.http_status,
            "code": self.code,
            "msg": self.msg,
            "log_id": self.log_id,
            "raw_error": self.raw_error,
        }


class FeishuClient:
    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self.config = load_feishu_config()
        if overrides:
            self.config.update({key: value for key, value in overrides.items() if value})
        self._token: str | None = None

    def access_token(self) -> str:
        user_token = self.config.get("user_access_token")
        if user_token:
            return user_token
        return self.tenant_access_token()

    def tenant_access_token(self, refresh: bool = False) -> str:
        if self._token and not refresh:
            return self._token
        app_id = self.config.get("app_id")
        app_secret = self.config.get("app_secret")
        if not app_id or not app_secret:
            raise FeishuApiError("缺少 FEISHU_APP_ID / FEISHU_APP_SECRET")
        data = self.request(
            "POST",
            "/auth/v3/tenant_access_token/internal",
            auth=False,
            payload={"app_id": app_id, "app_secret": app_secret},
        )
        token = data.get("tenant_access_token")
        if not token:
            raise FeishuApiError("Feishu 未返回 tenant_access_token", raw_error=data)
        self._token = token
        return token

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        retries: int = 1,
    ) -> dict[str, Any]:
        request_url = API_BASE + path
        headers: dict[str, str] = {}
        if auth:
            headers["Authorization"] = f"Bearer {self.access_token()}"
        if files is None:
            headers["Content-Type"] = "application/json; charset=utf-8"

        for attempt in range(retries + 1):
            response = requests.request(
                method,
                request_url,
                headers=headers,
                json=payload if files is None else None,
                data=payload if files is not None else None,
                params={k: v for k, v in (params or {}).items() if v is not None},
                files=files,
                timeout=45,
            )
            text = response.text
            try:
                data = response.json() if text else {}
            except Exception:
                data = {"raw": text}

            code = data.get("code", 0) if isinstance(data, dict) else ""
            if response.status_code < 400 and code == 0:
                return data

            if code in {99991663, 99991664} and auth and attempt == 0:
                headers["Authorization"] = f"Bearer {self.tenant_access_token(refresh=True)}"
                continue
            if attempt < retries:
                time.sleep(1.2 * (attempt + 1))
                continue

            msg = data.get("msg", "") if isinstance(data, dict) else str(data)
            log_id = data.get("error", {}).get("log_id", "") if isinstance(data, dict) else ""
            if not log_id and isinstance(data, dict):
                log_id = data.get("log_id", "")
            raise FeishuApiError(
                explain_feishu_error(response.status_code, code, msg),
                request_url=request_url,
                http_status=response.status_code,
                code=code,
                msg=msg,
                log_id=log_id,
                raw_error=data,
            )
        raise FeishuApiError("Feishu 请求失败", request_url=request_url)


def explain_feishu_error(http_status: int, code: Any, msg: str) -> str:
    if str(code) == "131005":
        return "目标文档、目标块或多维表格资源未找到，不是内容格式问题"
    if http_status in {401, 403}:
        return "应用没有目标资源权限，请把飞书应用加入文档/多维表格协作者并开放云文档权限"
    if "permission" in msg.lower():
        return "permission denied：应用没有编辑权限"
    return f"HTTP {http_status}: code={code}, msg={msg}"


def extract_wiki_token(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value.strip())
    path = parsed.path if parsed.scheme else value.strip()
    match = re.search(r"/wiki/([^/?#]+)", path)
    if match:
        return match.group(1)
    if "/" not in value and "?" not in value and "#" not in value:
        return value.strip()
    return ""


def extract_docx_token(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value.strip())
    path = parsed.path if parsed.scheme else value.strip()
    match = re.search(r"/docx/([^/?#]+)", path)
    if match:
        return match.group(1)
    if "/" not in value and "?" not in value and "#" not in value:
        return value.strip()
    return ""


def parse_bitable_url(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    parsed = urlparse(value.strip())
    path = parsed.path
    output: dict[str, str] = {}
    app_match = re.search(r"/base/([^/?#]+)", path)
    if app_match:
        output["app_token"] = app_match.group(1)
    table_match = re.search(r"[?&#]table=([^&#]+)", value)
    if table_match:
        output["table_id"] = table_match.group(1)
    view_match = re.search(r"[?&#]view=([^&#]+)", value)
    if view_match:
        output["view_id"] = view_match.group(1)
    return output


def text_block(content: str, block_type: int = 2) -> dict[str, Any]:
    key = {
        2: "text",
        3: "heading1",
        4: "heading2",
        5: "heading3",
        6: "heading4",
        7: "heading5",
        8: "heading6",
    }.get(block_type, "text")
    return {"block_type": block_type, key: {"elements": [{"text_run": {"content": content}}]}}
