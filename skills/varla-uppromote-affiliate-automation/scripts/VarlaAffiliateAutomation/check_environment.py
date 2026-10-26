#!/usr/bin/env python3
import json
import importlib.util
import sys
from pathlib import Path

from varla_affiliate import DEFAULT_DOCX, DEFAULT_GMAIL_TOKEN, DEFAULT_NODE, DEFAULT_NODE_MODULES, FEISHU_HELPER


def main():
    adspower_roots = [Path(r"E:\.ADSPOWER_GLOBAL\cache"), Path(r"C:\.ADSPOWER_GLOBAL\cache")]
    markers = []
    for root in adspower_roots:
        if root.is_dir():
            markers.extend(root.glob("*/DevToolsActivePort"))
    checks = {
        "python": Path(sys.executable).is_file(),
        "python_dependencies": all(
            importlib.util.find_spec(name) is not None
            for name in ("docx", "requests", "google.auth")
        ),
        "feishu_helper": FEISHU_HELPER.is_file(),
        "feishu_config": (Path.home() / ".feishu-docs/config.json").is_file(),
        "gmail_token": DEFAULT_GMAIL_TOKEN.is_file(),
        "docx_template": DEFAULT_DOCX.is_file(),
        "node": DEFAULT_NODE.is_file(),
        "playwright_modules": DEFAULT_NODE_MODULES.is_dir(),
        "adspower_running_marker": bool(markers),
    }
    print(json.dumps({"status": "ok" if all(checks.values()) else "needs_attention", "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
