#!/usr/bin/env python3
r"""Small Feishu document manager for Codex-local workflows.

Credentials are read from environment variables or a local config file:
  %USERPROFILE%\.feishu-docs\config.json

This tool intentionally keeps imports plain-text first. It is meant to provide
Codex with a reliable Feishu OpenAPI layer without asking the user to paste
secrets into chat.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://open.feishu.cn/open-apis"
CONFIG_DIR = Path.home() / ".feishu-docs"
CONFIG_PATH = CONFIG_DIR / "config.json"


class FeishuError(RuntimeError):
    pass


def load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    if CONFIG_PATH.exists():
        config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))

    env_map = {
        "app_id": "FEISHU_APP_ID",
        "app_secret": "FEISHU_APP_SECRET",
        "default_folder_token": "FEISHU_FOLDER_TOKEN",
    }
    for key, env_name in env_map.items():
        value = os.environ.get(env_name)
        if value:
            config[key] = value
    return config


def save_config(config: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def http_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = API_BASE + path
    if query:
        clean_query = {k: v for k, v in query.items() if v is not None}
        url += "?" + urllib.parse.urlencode(clean_query)

    body = None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise FeishuError(f"HTTP {exc.code} {exc.reason}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise FeishuError(f"Network error: {exc}") from exc

    if not raw:
        return {}
    data = json.loads(raw)
    code = data.get("code", 0)
    if code != 0:
        msg = data.get("msg") or data.get("message") or "unknown error"
        raise FeishuError(f"Feishu API error {code}: {msg}\n{json.dumps(data, ensure_ascii=False)}")
    return data


def get_tenant_access_token(config: dict[str, str]) -> str:
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    if not app_id or not app_secret:
        raise FeishuError(
            f"Missing app_id/app_secret. Run: python {Path(__file__).name} configure"
        )

    data = http_json(
        "POST",
        "/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    token = data.get("tenant_access_token")
    if not token:
        raise FeishuError("Feishu did not return tenant_access_token.")
    return token


def parse_markdown_as_text_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Keep imports schema-stable: strip common Markdown markers but create
        # only Feishu text blocks. Rich block mapping can be added after the app
        # permissions and document endpoints are verified on this tenant.
        while line.startswith("#"):
            line = line[1:].lstrip()
        if line.startswith(("- ", "* ")):
            line = "• " + line[2:].lstrip()
        elif len(line) > 3 and line[0].isdigit() and ". " in line[:5]:
            line = line.split(". ", 1)[1].lstrip()

        blocks.append(
            {
                "block_type": 2,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": line,
                            }
                        }
                    ]
                },
            }
        )
    return blocks


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def document_url(document_id: str) -> str:
    return f"https://feishu.cn/docx/{document_id}"


def cmd_configure(args: argparse.Namespace) -> None:
    current = load_config()
    app_id = args.app_id or input(f"Feishu app_id [{current.get('app_id', '')}]: ").strip()
    if not app_id:
        app_id = current.get("app_id", "")

    if args.app_secret:
        app_secret = args.app_secret
    else:
        prompt = "Feishu app_secret (input hidden"
        if current.get("app_secret"):
            prompt += ", press Enter to keep existing"
        prompt += "): "
        entered = getpass.getpass(prompt)
        app_secret = entered or current.get("app_secret", "")

    if args.no_folder_token:
        folder_token = ""
    else:
        folder_token = args.folder_token
    if folder_token is None:
        folder_token = input(
            f"Default folder_token, optional [{current.get('default_folder_token', '')}]: "
        ).strip()
    if not folder_token:
        folder_token = current.get("default_folder_token", "")

    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "default_folder_token": folder_token,
    }
    save_config({key: value for key, value in config.items() if value})
    print(f"Saved local Feishu config: {CONFIG_PATH}")


def cmd_check(args: argparse.Namespace) -> None:
    token = get_tenant_access_token(load_config())
    masked = token[:8] + "..." + token[-6:]
    print(f"OK: tenant_access_token acquired ({masked})")


def create_document(token: str, title: str, folder_token: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token
    data = http_json("POST", "/docx/v1/documents", token=token, payload=payload)
    doc = data.get("data", {}).get("document", {})
    document_id = doc.get("document_id") or data.get("data", {}).get("document_id")
    if not document_id:
        raise FeishuError(f"Create document returned no document_id: {json.dumps(data, ensure_ascii=False)}")
    doc["document_id"] = document_id
    return doc


def append_blocks(token: str, document_id: str, blocks: list[dict[str, Any]]) -> None:
    if not blocks:
        return
    for part in chunked(blocks, 50):
        http_json(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{document_id}/children",
            token=token,
            query={"document_revision_id": -1},
            payload={"children": part, "index": -1},
        )


def cmd_create(args: argparse.Namespace) -> None:
    config = load_config()
    token = get_tenant_access_token(config)
    folder_token = args.folder_token or config.get("default_folder_token")
    doc = create_document(token, args.title, folder_token)
    print(json.dumps({"document_id": doc["document_id"], "url": document_url(doc["document_id"])}, ensure_ascii=False, indent=2))


def cmd_import_markdown(args: argparse.Namespace) -> None:
    source = Path(args.file).expanduser().resolve()
    if not source.exists():
        raise FeishuError(f"File not found: {source}")

    config = load_config()
    token = get_tenant_access_token(config)
    folder_token = args.folder_token or config.get("default_folder_token")
    title = args.title or source.stem
    markdown = source.read_text(encoding=args.encoding)
    blocks = parse_markdown_as_text_blocks(markdown)
    doc = create_document(token, title, folder_token)
    append_blocks(token, doc["document_id"], blocks)
    print(
        json.dumps(
            {
                "document_id": doc["document_id"],
                "url": document_url(doc["document_id"]),
                "imported_blocks": len(blocks),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_append(args: argparse.Namespace) -> None:
    config = load_config()
    token = get_tenant_access_token(config)
    if args.file:
        text = Path(args.file).expanduser().resolve().read_text(encoding=args.encoding)
    else:
        text = args.text
    append_blocks(token, args.document_id, parse_markdown_as_text_blocks(text))
    print(f"OK: appended content to {document_url(args.document_id)}")


def cmd_read(args: argparse.Namespace) -> None:
    token = get_tenant_access_token(load_config())
    try:
        data = http_json(
            "GET",
            f"/docx/v1/documents/{args.document_id}/raw_content",
            token=token,
        )
    except FeishuError as first_error:
        try:
            data = http_json(
                "GET",
                f"/docx/v1/documents/{args.document_id}/plain_text",
                token=token,
            )
        except FeishuError:
            raise first_error
    content = data.get("data", {}).get("content") or data.get("data", {}).get("text") or data.get("data")
    if isinstance(content, (dict, list)):
        print(json.dumps(content, ensure_ascii=False, indent=2))
    else:
        print(content or "")


def cmd_list_folder(args: argparse.Namespace) -> None:
    config = load_config()
    token = get_tenant_access_token(config)
    folder_token = args.folder_token or config.get("default_folder_token")
    if not folder_token:
        raise FeishuError("Missing folder_token. Pass --folder-token or configure a default.")

    data = http_json(
        "GET",
        "/drive/v1/files",
        token=token,
        query={"folder_token": folder_token, "page_size": args.page_size},
    )
    print(json.dumps(data.get("data", data), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Feishu docs from local Codex workflows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python scripts\\feishu_docs.py configure
              python scripts\\feishu_docs.py check
              python scripts\\feishu_docs.py import-markdown ".\\doc.md" --title "Internal Doc"
              python scripts\\feishu_docs.py read <document_id>
            """
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure", help="Save local app_id/app_secret/folder_token.")
    configure.add_argument("--app-id")
    configure.add_argument("--app-secret")
    configure.add_argument("--folder-token")
    configure.add_argument("--no-folder-token", action="store_true")
    configure.set_defaults(func=cmd_configure)

    check = subparsers.add_parser("check", help="Verify that app credentials can get a tenant token.")
    check.set_defaults(func=cmd_check)

    create = subparsers.add_parser("create", help="Create an empty Feishu docx document.")
    create.add_argument("--title", required=True)
    create.add_argument("--folder-token")
    create.set_defaults(func=cmd_create)

    import_md = subparsers.add_parser("import-markdown", help="Create a doc and import a Markdown file as text blocks.")
    import_md.add_argument("file")
    import_md.add_argument("--title")
    import_md.add_argument("--folder-token")
    import_md.add_argument("--encoding", default="utf-8")
    import_md.set_defaults(func=cmd_import_markdown)

    append = subparsers.add_parser("append", help="Append text or Markdown content to an existing doc.")
    append.add_argument("document_id")
    source = append.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file")
    append.add_argument("--encoding", default="utf-8")
    append.set_defaults(func=cmd_append)

    read = subparsers.add_parser("read", help="Read a Feishu doc as raw/plain text.")
    read.add_argument("document_id")
    read.set_defaults(func=cmd_read)

    list_folder = subparsers.add_parser("list-folder", help="List files in a Feishu drive folder.")
    list_folder.add_argument("--folder-token")
    list_folder.add_argument("--page-size", type=int, default=50)
    list_folder.set_defaults(func=cmd_list_folder)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except FeishuError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
