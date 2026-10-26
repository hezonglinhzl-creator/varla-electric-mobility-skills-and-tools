#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any


DESTINATION = "https://varlascooter.com/collections/electric-dirt-bike"
ADMIN_URL = "https://admin.shopify.com/store/varla-scooterus/apps/affliate-by-secomapp/admin/affiliates?menu=true"
EMAIL_SUBJECT = "Varla Affiliate Code & Tracking Link"
EXPECTED_GMAIL = "info@varlascooter.com"
FEISHU_HELPER = Path.home() / ".codex/skills/feishu-codex-local/scripts/feishu_docs.py"
PACKAGED_DOCX = Path(__file__).resolve().parent / "assets" / "Varla KOL Code.docx"
DEFAULT_DOCX = PACKAGED_DOCX if PACKAGED_DOCX.is_file() else Path.home() / "Downloads/合作合同/Varla KOL Code.docx"
DEFAULT_GMAIL_TOKEN = Path.home() / "AppData/Local/VarlaKOLCommandCenter/gmail-token.json"
DEFAULT_NODE = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
DEFAULT_NODE_MODULES = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"


class WorkflowError(RuntimeError):
    pass


class ExistingLinkError(WorkflowError):
    pass


@dataclass(frozen=True)
class FeishuRef:
    app_token: str
    table_id: str
    view_id: str | None


@dataclass(frozen=True)
class Creator:
    record_id: str
    name: str
    email: str
    code: str
    existing_link: str | None = None


def parse_feishu_url(url: str) -> FeishuRef:
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    try:
        app_token = parts[parts.index("base") + 1]
    except (ValueError, IndexError):
        raise WorkflowError("飞书链接中缺少 Base app token") from None
    query = urllib.parse.parse_qs(parsed.query)
    table_id = (query.get("table") or [""])[0]
    if not table_id:
        raise WorkflowError("飞书链接中缺少 table 参数")
    view_id = (query.get("view") or [None])[0]
    return FeishuRef(app_token, table_id, view_id)


def normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_name(value: Any) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _field_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("link") or "").strip()
    if isinstance(value, list):
        return "".join(_field_text(item) for item in value).strip()
    return str(value or "").strip()


def choose_record(
    records: list[dict[str, Any]], *, email: str | None = None,
    kol_name: str | None = None, code_name: str | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    if not any((email, kol_name, code_name, record_id)):
        raise WorkflowError("必须使用 --email 或 --kol-name 精确指定一个 KOL")
    matches = []
    for record in records:
        fields = record.get("fields", {})
        email_match = email and normalize_email(fields.get("Email")) == normalize_email(email)
        name_match = kol_name and normalize_name(fields.get("KOL Name")) == normalize_name(kol_name)
        code_match = code_name and normalize_name(fields.get("code name")) == normalize_name(code_name)
        id_match = record_id and str(record.get("record_id") or "") == record_id
        if email_match or name_match or code_match or id_match:
            matches.append(record)
    if len(matches) != 1:
        raise WorkflowError(f"飞书记录匹配数量应为 1，实际为 {len(matches)}")
    return matches[0]


def extract_existing_link(value: Any) -> str | None:
    text = _field_text(value)
    return text or None


def validate_record(record: dict[str, Any], *, allow_existing_link: bool = False) -> Creator:
    fields = record.get("fields", {})
    creator = Creator(
        record_id=str(record.get("record_id") or ""),
        name=_field_text(fields.get("KOL Name")),
        email=normalize_email(fields.get("Email")),
        code=_field_text(fields.get("code name")),
        existing_link=extract_existing_link(fields.get("code link")),
    )
    missing = [key for key, value in (("record_id", creator.record_id), ("KOL Name", creator.name), ("Email", creator.email), ("code name", creator.code)) if not value]
    if missing:
        raise WorkflowError("飞书记录缺少字段：" + ", ".join(missing))
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", creator.email):
        raise WorkflowError("飞书 Email 格式无效")
    if creator.existing_link and not allow_existing_link:
        raise ExistingLinkError(f"该记录已有 code link：{creator.existing_link}")
    return creator


def safe_creator_name(name: str) -> str:
    cleaned = "".join(
        ch for ch in name
        if unicodedata.category(ch)[0] in {"L", "N"} or ch in {" ", "-", "'", "."}
    )
    return " ".join(cleaned.split()).strip(" .-") or name.strip()


def split_creator_name(name: str) -> tuple[str, str]:
    safe_name = safe_creator_name(name)
    parts = safe_name.split()
    # UpPromote validates an unsplit PascalCase handle such as JustDoItTray as
    # an invalid first name.  Split only clear component boundaries from the
    # supplied handle; this does not invent a surname and leaves one-word
    # handles unchanged.
    if len(parts) == 1:
        camel_parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", safe_name)
        if len(camel_parts) > 1 and "".join(camel_parts) == safe_name:
            parts = camel_parts
    return (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (safe_name, "-")


def url_field(link: str) -> dict[str, str]:
    if not re.fullmatch(r"https://[^\s]+", link):
        raise WorkflowError("短链接不是有效 HTTPS URL")
    return {"link": link, "text": link}


def render_email_template(template: str, creator: str, code: str, link: str) -> str:
    replacements = {"[Creator Name]": creator, "[CODE]": code, "[LINK]": link}
    rendered = template
    for old, new in replacements.items():
        rendered = rendered.replace(old, new)
    unresolved = re.findall(r"\[[A-Za-z ]+\]", rendered)
    if unresolved:
        raise WorkflowError("邮件模板仍有未替换字段：" + ", ".join(sorted(set(unresolved))))
    return rendered.strip()


def read_docx_email(path: Path) -> tuple[str, str]:
    from docx import Document

    document = Document(path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    if len(paragraphs) < 2:
        raise WorkflowError("DOCX 邮件模板正文为空或格式不完整")
    return paragraphs[0].strip(), "\n\n".join(paragraphs[1:]).strip() + "\n"


def build_email_message(*, sender: str, recipient: str, subject: str, body: str) -> EmailMessage:
    if normalize_email(sender) != EXPECTED_GMAIL:
        raise WorkflowError(f"发件邮箱必须是 {EXPECTED_GMAIL}")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalize_email(recipient)):
        raise WorkflowError("收件邮箱格式无效")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = normalize_email(recipient)
    message["Subject"] = subject.replace("\r", " ").replace("\n", " ")
    message.set_content(body)
    return message


def email_body_matches(body: str, code: str, link: str) -> bool:
    return code in body and link in body


def build_gmail_query(folder: str, recipient: str, subject: str) -> str:
    if folder not in {"drafts", "sent"}:
        raise WorkflowError(f"Unsupported Gmail folder: {folder}")
    safe_subject = subject.replace("\\", "\\\\").replace('"', '\\"')
    return f'in:{folder} to:{normalize_email(recipient)} subject:"{safe_subject}" newer_than:90d'


def duplicate_delivery_action(send: bool, duplicate: dict[str, Any] | None) -> str:
    if not duplicate:
        return "create_new"
    if send and duplicate.get("status") == "existing_draft":
        return "send_existing_draft"
    return "return_existing"


def draft_resource_id(duplicate: dict[str, Any] | None) -> str:
    return str((duplicate or {}).get("draft_id") or "")


def progress(stage: str, message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {stage}: {message}", flush=True)


def console_json_text(payload: Any, encoding: str | None, *, indent: int | None = 2) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    try:
        text.encode(encoding or "utf-8")
        return text
    except (LookupError, UnicodeEncodeError):
        return json.dumps(payload, ensure_ascii=True, indent=indent)


def print_console_json(payload: Any, *, stream: Any = None, indent: int | None = 2) -> None:
    target = stream or sys.stdout
    print(console_json_text(payload, getattr(target, "encoding", None), indent=indent), file=target)


def parse_worker_result(lines: list[str]) -> dict[str, Any]:
    prefix = "VARLA_RESULT::"
    marker = next((line[len(prefix):] for line in reversed(lines) if line.startswith(prefix)), None)
    if not marker:
        raise WorkflowError("UpPromote worker did not return a structured result")
    return json.loads(marker)


def _load_feishu_helper():
    if not FEISHU_HELPER.is_file():
        raise WorkflowError(f"未找到飞书工具：{FEISHU_HELPER}")
    spec = importlib.util.spec_from_file_location("feishu_docs_local", FEISHU_HELPER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FeishuClient:
    def __init__(self, ref: FeishuRef):
        helper = _load_feishu_helper()
        self.helper = helper
        self.ref = ref
        self.token = helper.get_tenant_access_token(helper.load_config())

    def list_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token = None
        while True:
            query = {"page_size": 500, "view_id": self.ref.view_id, "page_token": page_token}
            data = self.helper.http_json(
                "GET",
                f"/bitable/v1/apps/{self.ref.app_token}/tables/{self.ref.table_id}/records",
                token=self.token,
                query=query,
            ).get("data", {})
            records.extend(data.get("items", []))
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token")

    def get_record(self, record_id: str) -> dict[str, Any]:
        data = self.helper.http_json(
            "GET",
            f"/bitable/v1/apps/{self.ref.app_token}/tables/{self.ref.table_id}/records/{record_id}",
            token=self.token,
        ).get("data", {})
        return data.get("record") or data

    def writeback(self, creator: Creator, link: str) -> dict[str, Any]:
        self.helper.http_json(
            "PUT",
            f"/bitable/v1/apps/{self.ref.app_token}/tables/{self.ref.table_id}/records/{creator.record_id}",
            token=self.token,
            payload={"fields": {"code name": creator.code, "code link": url_field(link)}},
        )
        reread = self.get_record(creator.record_id)
        fields = reread.get("fields", {})
        if _field_text(fields.get("code name")) != creator.code or extract_existing_link(fields.get("code link")) != link:
            raise WorkflowError("飞书回读验证失败")
        return reread


def locate_python() -> Path:
    current = Path(sys.executable)
    if current.is_file():
        return current
    raise WorkflowError("未找到 Python 运行环境")


def run_browser_worker(payload: dict[str, Any], worker: Path, node: Path = DEFAULT_NODE) -> dict[str, Any]:
    if not node.is_file():
        raise WorkflowError(f"未找到 Node.js：{node}")
    if not worker.is_file():
        raise WorkflowError(f"未找到 UpPromote worker：{worker}")
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        input_path = Path(handle.name)
    env = dict(__import__("os").environ)
    env["NODE_PATH"] = str(DEFAULT_NODE_MODULES)
    output: list[str] = []
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            [str(node), str(worker), str(input_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env,
        )
        assert process.stdout is not None

        def read_output() -> None:
            for raw_line in process.stdout:
                line = raw_line.rstrip("\r\n")
                output.append(line)
                if line.startswith("VARLA_PROGRESS::"):
                    event = json.loads(line[16:])
                    progress(event.get("stage", "browser"), event.get("status", "working"))

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        deadline = time.monotonic() + 300
        while process.poll() is None:
            if time.monotonic() >= deadline:
                process.terminate()
                raise WorkflowError("UpPromote worker exceeded 300 seconds and was stopped")
            time.sleep(0.1)
        reader.join(timeout=2)
    finally:
        input_path.unlink(missing_ok=True)
    if process is None or process.returncode:
        raise WorkflowError(("\n".join(output) or "UpPromote worker failed").strip())
    return parse_worker_result(output)


class GmailClient:
    def __init__(self, token_path: Path):
        from google.auth.transport.requests import AuthorizedSession, Request
        from google.oauth2.credentials import Credentials

        credentials = Credentials.from_authorized_user_file(token_path)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        self.session = AuthorizedSession(credentials)
        self.root = "https://gmail.googleapis.com/gmail/v1/users/me"
        profile = self.session.get(f"{self.root}/profile", timeout=30)
        profile.raise_for_status()
        account = normalize_email(profile.json().get("emailAddress"))
        if account != EXPECTED_GMAIL:
            raise WorkflowError(f"Gmail 登录账号为 {account}，必须是 {EXPECTED_GMAIL}")

    @staticmethod
    def _decode_raw(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def _read_raw_message(self, message_id: str) -> EmailMessage:
        response = self.session.get(f"{self.root}/messages/{message_id}", params={"format": "raw"}, timeout=30)
        response.raise_for_status()
        return BytesParser(policy=policy.default).parsebytes(self._decode_raw(response.json()["raw"]))

    def find_duplicate(self, message: EmailMessage) -> dict[str, Any] | None:
        recipient = normalize_email(message.get("To"))
        subject = str(message.get("Subject"))
        body_part = message.get_body(preferencelist=("plain",))
        wanted = body_part.get_content() if body_part else ""
        code_match = re.search(r"Discount Code:\s*([^\s]+)", wanted)
        link_match = re.search(r"Affiliate Link:\s*(https://[^\s]+)", wanted)
        if not code_match or not link_match:
            raise WorkflowError("无法从邮件正文识别 code/link，停止防重复检查")
        code, link = code_match.group(1), link_match.group(1)

        drafts = self.session.get(
            f"{self.root}/drafts",
            params={"q": build_gmail_query("drafts", recipient, subject), "maxResults": 20},
            timeout=30,
        )
        drafts.raise_for_status()
        for item in drafts.json().get("drafts", []):
            message_item = item.get("message", {})
            parsed = self._read_raw_message(message_item["id"])
            part = parsed.get_body(preferencelist=("plain",))
            body = part.get_content() if part else ""
            if normalize_email(parsed.get("To")) == recipient and str(parsed.get("Subject")) == subject and email_body_matches(body, code, link):
                return {"status": "existing_draft", "draft_id": item.get("id"), "message": message_item}

        sent = self.session.get(
            f"{self.root}/messages",
            params={"q": build_gmail_query("sent", recipient, subject), "maxResults": 20},
            timeout=30,
        )
        sent.raise_for_status()
        for item in sent.json().get("messages", []):
            parsed = self._read_raw_message(item["id"])
            part = parsed.get_body(preferencelist=("plain",))
            body = part.get_content() if part else ""
            if email_body_matches(body, code, link):
                return {"status": "already_sent", "message": item}
        return None

    def _find_draft_id_for_message(self, message_id: str) -> str | None:
        page_token = None
        for _ in range(10):
            params: dict[str, Any] = {"maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
            response = self.session.get(f"{self.root}/drafts", params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("drafts", []):
                if item.get("message", {}).get("id") == message_id:
                    return item.get("id")
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return None

    def deliver(self, message: EmailMessage, *, send: bool, confirm: str | None) -> dict[str, Any]:
        if send and confirm != "SEND":
            raise WorkflowError("真实发送必须同时提供 --send --confirm SEND")
        duplicate = self.find_duplicate(message)
        action = duplicate_delivery_action(send, duplicate)
        if action == "return_existing":
            return duplicate
        if action == "send_existing_draft":
            message_id = str((duplicate or {}).get("message", {}).get("id") or "")
            draft_id = draft_resource_id(duplicate) or self._find_draft_id_for_message(message_id)
            if not draft_id:
                raise WorkflowError("已核验草稿的 draft ID 不存在，未执行发送")
            sent_response = self.session.post(f"{self.root}/drafts/send", json={"id": draft_id}, timeout=30)
            sent_response.raise_for_status()
            sent = sent_response.json()
            if not sent.get("id"):
                raise WorkflowError("Gmail 发送结果缺少 message ID，需要人工核对，禁止重发")
            return {"status": "sent", "message": sent}
        raw = base64.urlsafe_b64encode(message.as_bytes(policy=policy.SMTP)).decode("ascii").rstrip("=")
        draft_response = self.session.post(f"{self.root}/drafts", json={"message": {"raw": raw}}, timeout=30)
        draft_response.raise_for_status()
        draft = draft_response.json()
        if not send:
            return {"status": "draft_created", "draft_id": draft.get("id"), "message": draft.get("message", {})}
        sent_response = self.session.post(f"{self.root}/drafts/send", json={"id": draft.get("id")}, timeout=30)
        sent_response.raise_for_status()
        return {"status": "sent", "message": sent_response.json()}


def save_audit(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Varla UpPromote Affiliate 全流程自动化")
    parser.add_argument("--feishu-url", required=True, help="飞书 Base 表格/视图链接")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--email", help="用邮箱精确匹配飞书记录")
    selector.add_argument("--kol-name", help="用 KOL Name 精确匹配飞书记录")
    selector.add_argument("--code-name", help="用飞书 code name 精确匹配记录")
    selector.add_argument("--record-id", help="用飞书 record ID 直接读取记录（最快）")
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX, help="邮件模板 DOCX")
    parser.add_argument("--dry-run", action="store_true", help="只读取和校验，不执行任何外部写入")
    parser.add_argument("--resume-existing-link", action="store_true", help="已有 code link 时仅继续邮件阶段")
    parser.add_argument("--send", action="store_true", help="发送邮件；默认只创建草稿")
    parser.add_argument("--confirm", help="真实发送时必须为 SEND")
    parser.add_argument("--gmail-token", type=Path, default=DEFAULT_GMAIL_TOKEN)
    parser.add_argument("--node", type=Path, default=DEFAULT_NODE)
    parser.add_argument("--browser-timeout", type=int, default=180000)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.send and args.confirm != "SEND":
        raise WorkflowError("真实发送必须同时提供 --send --confirm SEND")
    progress("Feishu", "locating creator record")
    ref = parse_feishu_url(args.feishu_url)
    feishu = FeishuClient(ref)
    if args.record_id:
        chosen = feishu.get_record(args.record_id)
    else:
        chosen = choose_record(
            feishu.list_records(), email=args.email, kol_name=args.kol_name,
            code_name=args.code_name,
        )
    creator = validate_record(chosen, allow_existing_link=args.resume_existing_link)
    subject, template = read_docx_email(args.docx)
    first_name, last_name = split_creator_name(creator.name)
    # Keep the browser-detail lookup aligned with the normalized name that was
    # actually saved in UpPromote (for example Just Do It Tray).
    email_name = " ".join(part for part in (first_name, last_name) if part != "-")
    audit: dict[str, Any] = {
        "started_at": datetime.now().astimezone().isoformat(),
        "creator": asdict(creator),
        "feishu": asdict(ref),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        audit["status"] = "dry_run_ok"
        audit["planned"] = {"program": "KOL - $100", "destination": DESTINATION, "email_mode": "send" if args.send else "draft"}
        print_console_json(audit)
        return 0

    if creator.existing_link:
        short_link = creator.existing_link
        audit["affiliate"] = {"status": "skipped_existing_link"}
    else:
        progress("UpPromote", "connecting AdsPower and checking affiliate")
        browser_payload = {
            "adminUrl": ADMIN_URL,
            "destination": DESTINATION,
            "creator": {"firstName": first_name, "lastName": last_name, "name": email_name, "email": creator.email, "code": creator.code},
            "timeoutMs": args.browser_timeout,
        }
        browser_result = run_browser_worker(browser_payload, Path(__file__).with_name("uppromote_worker.cjs"), args.node)
        short_link = browser_result.get("shortLink", "")
        url_field(short_link)
        audit["affiliate"] = browser_result
        progress("Feishu", "writing code/link and verifying reread")
        feishu.writeback(creator, short_link)
        audit["feishu_writeback"] = "verified"

    body = render_email_template(template, email_name, creator.code, short_link)
    message = build_email_message(sender=EXPECTED_GMAIL, recipient=creator.email, subject=subject or EMAIL_SUBJECT, body=body)
    progress("Gmail", "checking duplicates and preparing delivery")
    gmail = GmailClient(args.gmail_token)
    audit["email"] = gmail.deliver(message, send=args.send, confirm=args.confirm)
    audit["status"] = "complete"
    audit["short_link"] = short_link
    audit["finished_at"] = datetime.now().astimezone().isoformat()
    audit_path = Path(__file__).with_name("logs") / f"{creator.record_id}-{datetime.now():%Y%m%d-%H%M%S}.json"
    save_audit(audit_path, audit)
    print_console_json({**audit, "audit_file": str(audit_path)})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExistingLinkError as exc:
        print_console_json({"status": "already_complete", "message": str(exc)}, stream=sys.stderr, indent=None)
        raise SystemExit(3)
    except WorkflowError as exc:
        print_console_json({"status": "stopped", "message": str(exc)}, stream=sys.stderr, indent=None)
        raise SystemExit(2)
