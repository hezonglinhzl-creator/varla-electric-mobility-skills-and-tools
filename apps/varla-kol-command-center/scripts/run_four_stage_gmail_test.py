from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import importlib.util
import time
from typing import Any, Callable, Sequence
from uuid import uuid4

try:
    from four_stage_test_content import STAGE_SLUGS, exact_body, exact_subject
except ModuleNotFoundError:
    _content_path = Path(__file__).with_name("four_stage_test_content.py")
    _content_spec = importlib.util.spec_from_file_location(
        "varla_four_stage_runner_content", _content_path
    )
    if _content_spec is None or _content_spec.loader is None:
        raise
    _content = importlib.util.module_from_spec(_content_spec)
    _content_spec.loader.exec_module(_content)
    STAGE_SLUGS = _content.STAGE_SLUGS
    exact_body = _content.exact_body
    exact_subject = _content.exact_subject


EXPECTED_SENDER = "info@varlascooter.com"
TEST_RECIPIENT = "test@example.com"
RUN_ID_PATTERN = re.compile(r"KOLTEST-\d{8}-\d{6}\Z")
DOCX_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
SCHEMA = "varla-kol-four-stage-test-package"
ProcessRunner = Callable[[Sequence[str], float], dict[str, Any]]


class SafetyStop(RuntimeError):
    """Fail-closed stop. The caller must reconcile before attempting anything else."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_reparse_or_symlink(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _regular(path: Path, label: str) -> Path:
    try:
        if _is_reparse_or_symlink(path) or not path.is_file():
            raise SafetyStop(f"{label} must be a regular non-reparse file")
    except OSError as exc:
        raise SafetyStop(f"{label} cannot be inspected") from exc
    return path.resolve(strict=True)


def _contained_file(root: Path, supplied: object, label: str) -> Path:
    if type(supplied) is not str or not supplied:
        raise SafetyStop(f"{label} path is invalid")
    relative = Path(supplied)
    if relative.is_absolute() or ".." in relative.parts or relative.name != supplied:
        raise SafetyStop(f"{label} must be a simple relative filename")
    candidate = root / relative
    resolved = _regular(candidate, label)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SafetyStop(f"{label} escapes package root") from exc
    return resolved


def _exact_keys(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise SafetyStop(f"{label} schema is invalid")
    return value


def _validate_file_metadata(
    root: Path, metadata: object, label: str, expected_name: str | None = None
) -> tuple[Path, dict[str, Any]]:
    item = _exact_keys(
        metadata, {"path", "filename", "bytes", "sha256", "content_type"}, label
    )
    path = _contained_file(root, item["path"], label)
    if item["filename"] != path.name or (
        expected_name is not None and path.name != expected_name
    ):
        raise SafetyStop(f"{label} filename mismatch")
    if type(item["filename"]) is not str or type(item["content_type"]) is not str:
        raise SafetyStop(f"{label} string metadata is invalid")
    if type(item["bytes"]) is not int or item["bytes"] <= 0:
        raise SafetyStop(f"{label} byte count is invalid")
    if item["bytes"] != path.stat().st_size:
        raise SafetyStop(f"{label} byte count mismatch")
    if (
        type(item["sha256"]) is not str
        or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        or item["sha256"] != _sha256(path)
    ):
        raise SafetyStop(f"{label} hash mismatch")
    if item["content_type"] != DOCX_TYPE:
        raise SafetyStop(f"{label} content type mismatch")
    return path, item


def load_and_validate_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        if _is_reparse_or_symlink(manifest_path.parent):
            raise SafetyStop("package root must not be a symlink or reparse point")
    except OSError as exc:
        raise SafetyStop("package root cannot be inspected") from exc
    manifest_resolved = _regular(manifest_path, "manifest")
    root = manifest_resolved.parent
    if _is_reparse_or_symlink(root):
        raise SafetyStop("package root must not be a symlink or reparse point")
    root = root.resolve(strict=True)
    try:
        manifest = json.loads(manifest_resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SafetyStop("manifest is not valid UTF-8 JSON") from exc
    top = _exact_keys(
        manifest,
        {
            "schema",
            "version",
            "run_id",
            "expected_sender",
            "locked_recipient",
            "source_hashes",
            "outputs",
            "messages",
        },
        "manifest",
    )
    run_id = top["run_id"]
    if type(top["schema"]) is not str or type(top["version"]) is not int:
        raise SafetyStop("manifest schema types are invalid")
    if top["schema"] != SCHEMA or top["version"] != 1:
        raise SafetyStop("unsupported manifest schema")
    if type(run_id) is not str or not RUN_ID_PATTERN.fullmatch(run_id):
        raise SafetyStop("run ID is invalid")
    if top["expected_sender"] != EXPECTED_SENDER:
        raise SafetyStop("sender lock failed")
    if top["locked_recipient"] != TEST_RECIPIENT:
        raise SafetyStop("recipient lock failed")

    hashes = _exact_keys(top["source_hashes"], {"contract", "requirements"}, "source hashes")
    for name in ("contract", "requirements"):
        pair = _exact_keys(hashes[name], {"before", "after"}, f"{name} source hash")
        if (
            type(pair["before"]) is not str
            or type(pair["after"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", pair["before"])
            or pair["before"] != pair["after"]
        ):
            raise SafetyStop(f"{name} source hash changed")

    outputs = top["outputs"]
    if type(outputs) is not list or len(outputs) != 2:
        raise SafetyStop("outputs must contain exactly two files")
    output_paths: list[Path] = []
    output_metadata: list[dict[str, Any]] = []
    for index, item in enumerate(outputs):
        path, metadata = _validate_file_metadata(root, item, f"output {index + 1}")
        output_paths.append(path)
        output_metadata.append(metadata)
    if len(set(output_paths)) != 2 or output_paths[0].name != (
        f"Varla_KOL_Agreement_TEST_ONLY_{run_id}.docx"
    ) or output_paths[1].name != "Varla_KOL_Content_Creation_Requirements_TEST_COPY.docx":
        raise SafetyStop("output filenames are invalid or duplicated")

    messages = top["messages"]
    if type(messages) is not list or len(messages) != 4:
        raise SafetyStop("messages must contain exactly four stages")
    seen_subjects: set[str] = set()
    used_files = {manifest_resolved}
    runtime_messages = []
    for index, message in enumerate(messages, start=1):
        item = _exact_keys(
            message,
            {
                "stage", "subject", "body_file", "body_bytes", "body_sha256",
                "eml_file", "attachments",
            },
            f"stage {index}",
        )
        if type(item["stage"]) is not int or item["stage"] != index:
            raise SafetyStop("stage sequence is invalid")
        subject = item["subject"]
        if (
            type(subject) is not str
            or subject != exact_subject(index, run_id)
            or subject in seen_subjects
        ):
            raise SafetyStop(f"stage {index} subject is invalid")
        seen_subjects.add(subject)
        body_name = f"stage-{index}-{STAGE_SLUGS[index - 1]}.txt"
        eml_name = f"stage-{index}-{STAGE_SLUGS[index - 1]}.eml"
        body_path = _contained_file(root, item["body_file"], f"stage {index} body")
        eml_path = _contained_file(root, item["eml_file"], f"stage {index} EML")
        if body_path.name != body_name or eml_path.name != eml_name:
            raise SafetyStop(f"stage {index} semantic filename mismatch")
        body_payload = body_path.read_bytes()
        if (
            type(item["body_bytes"]) is not int
            or item["body_bytes"] != len(body_payload)
            or type(item["body_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", item["body_sha256"])
            or item["body_sha256"] != hashlib.sha256(body_payload).hexdigest()
        ):
            raise SafetyStop(f"stage {index} body metadata mismatch")
        try:
            body_text = body_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafetyStop(f"stage {index} body is not UTF-8") from exc
        if body_text != exact_body(index, run_id):
            raise SafetyStop(f"stage {index} approved body mismatch")
        attachments = item["attachments"]
        if type(attachments) is not list:
            raise SafetyStop(f"stage {index} attachments are invalid")
        if (index == 3 and len(attachments) != 2) or (
            index != 3 and attachments
        ):
            raise SafetyStop(f"stage {index} attachment count is invalid")
        attachment_paths: list[Path] = []
        for attachment_index, attachment in enumerate(attachments):
            path, metadata = _validate_file_metadata(
                root, attachment, f"stage {index} attachment {attachment_index + 1}"
            )
            if metadata != output_metadata[attachment_index]:
                raise SafetyStop("stage 3 attachment metadata differs from outputs")
            attachment_paths.append(path)
        for path in (body_path, eml_path):
            if path in used_files:
                raise SafetyStop("duplicate package path")
            used_files.add(path)
        runtime_messages.append(
            {
                **item,
                "body_path": body_path,
                "body_metadata": {
                    "bytes": item["body_bytes"],
                    "sha256": item["body_sha256"],
                },
                "eml_path": eml_path,
                "attachment_paths": attachment_paths,
            }
        )

    expected_paths = {
        item.resolve()
        for item in root.iterdir()
        if item.is_file() and item.name != "test-result.json"
    }
    expected_manifest_paths = used_files | set(output_paths)
    if expected_paths != expected_manifest_paths:
        raise SafetyStop("package has extra or missing files")
    return {
        **top,
        "_root": root,
        "_manifest_path": manifest_resolved,
        "_messages": runtime_messages,
        "_output_paths": output_paths,
    }


def subprocess_json(args: Sequence[str], timeout: float) -> dict[str, Any]:
    try:
        result = subprocess.run(
            list(args), capture_output=True, text=True, encoding="utf-8",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyStop("Gmail command did not complete safely") from exc
    if result.returncode != 0:
        raise SafetyStop("Gmail command failed")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SafetyStop("Gmail command returned malformed JSON") from exc
    if not isinstance(parsed, dict):
        raise SafetyStop("Gmail command returned an invalid result")
    return parsed


def _atomic_result(path: Path, data: dict[str, Any]) -> None:
    if path.exists() and _is_reparse_or_symlink(path):
        raise SafetyStop("result path must not be a symlink or reparse point")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    payload = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)
        if hasattr(os, "O_DIRECTORY"):
            descriptor = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _common_args(
    python: Path, cli: Path, credentials: Path, token: Path
) -> list[str]:
    return [
        str(python), str(cli), "--credentials", str(credentials), "--token",
        str(token), "--expected-account", EXPECTED_SENDER,
    ]


def _safe_result(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "varla-kol-four-stage-test-result",
        "version": 1,
        "run_id": manifest["run_id"],
        "expected_sender": EXPECTED_SENDER,
        "locked_recipient": TEST_RECIPIENT,
        "state": "sending",
        "in_flight_stage": None,
        "attempt_started": False,
        "source_hashes": manifest["source_hashes"],
        "outputs": [
            {key: item[key] for key in ("filename", "bytes", "sha256", "content_type")}
            for item in manifest["outputs"]
        ],
        "completed_stages": [],
        "messages": [],
        "sent_verification": None,
    }


def _revalidate_send_inputs(manifest: dict[str, Any], message: dict[str, Any]) -> None:
    body_path = _regular(message["body_path"], f"stage {message['stage']} body")
    body_payload = body_path.read_bytes()
    body_metadata = message["body_metadata"]
    if (
        len(body_payload) != body_metadata["bytes"]
        or hashlib.sha256(body_payload).hexdigest() != body_metadata["sha256"]
        or body_payload.decode("utf-8") != exact_body(message["stage"], manifest["run_id"])
    ):
        raise SafetyStop("approved body changed after validation")
    for index, (path, metadata) in enumerate(
        zip(manifest["_output_paths"], manifest["outputs"], strict=True), start=1
    ):
        current = _regular(path, f"output {index}")
        if (
            current.name != metadata["filename"]
            or current.stat().st_size != metadata["bytes"]
            or _sha256(current) != metadata["sha256"]
        ):
            raise SafetyStop("attachment changed after validation")


def _failure_type(exc: Exception) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout"
    if isinstance(exc, SafetyStop):
        return "safety_stop"
    return "process_error"


def run_test(
    manifest_path: Path,
    *,
    cli: Path,
    credentials: Path,
    token: Path,
    confirm: str,
    process: ProcessRunner = subprocess_json,
    python: Path = Path(sys.executable),
    timeout: float = 60.0,
) -> dict[str, Any]:
    if confirm != "SEND":
        raise SafetyStop("explicit --confirm SEND is required")
    manifest = load_and_validate_manifest(manifest_path)
    cli = _regular(cli, "Gmail CLI")
    credentials = _regular(credentials, "credentials")
    token = _regular(token, "token")
    python = _regular(python, "Python executable")
    common = _common_args(python, cli, credentials, token)
    result_path = manifest["_root"] / "test-result.json"
    if result_path.exists():
        raise SafetyStop(
            "test-result.json already exists; inspect and reconcile it before any rerun"
        )
    verified = process([*common, "verify"], timeout)
    if not isinstance(verified, dict) or verified.get("status") != "ok" or (
        verified.get("account") != EXPECTED_SENDER
    ):
        raise SafetyStop("authenticated Gmail account verification failed")

    result = _safe_result(manifest)
    _atomic_result(result_path, result)
    for message in manifest["_messages"]:
        result["state"] = "sending"
        result["in_flight_stage"] = message["stage"]
        result["attempt_started"] = True
        _atomic_result(result_path, result)
        args = [
            *common, "compose", "--to", TEST_RECIPIENT, "--subject",
            message["subject"], "--body-file", str(message["body_path"]),
            "--expected-body-sha256", message["body_metadata"]["sha256"],
            "--expected-body-bytes", str(message["body_metadata"]["bytes"]),
            "--mode", "send", "--confirm", "SEND",
        ]
        for attachment, metadata in zip(
            message["attachment_paths"], message["attachments"], strict=True
        ):
            args.extend(
                [
                    "--attachment", str(attachment),
                    "--expected-attachment-sha256", metadata["sha256"],
                    "--expected-attachment-bytes", str(metadata["bytes"]),
                ]
            )
        try:
            _revalidate_send_inputs(manifest, message)
            sent = process(args, timeout)
        except Exception as exc:
            result["state"] = "needs_reconciliation"
            result["error_type"] = _failure_type(exc)
            _atomic_result(result_path, result)
            if isinstance(exc, SafetyStop):
                raise
            raise SafetyStop("send attempt failed; inspect result and do not retry") from exc
        if not isinstance(sent, dict):
            result["state"] = "needs_reconciliation"
            result["error_type"] = "malformed_result"
            _atomic_result(result_path, result)
            raise SafetyStop("send outcome is malformed; do not retry")
        message_id = sent.get("message_id")
        thread_id = sent.get("thread_id")
        if (
            sent.get("status") != "sent"
            or not isinstance(message_id, str) or not message_id
            or not isinstance(thread_id, str) or not thread_id
        ):
            result["state"] = "needs_reconciliation"
            result["error_type"] = "uncertain_result"
            _atomic_result(result_path, result)
            raise SafetyStop("send outcome is uncertain; do not retry")
        expected_attachment_summaries = [
            {
                "filename": item["filename"],
                "content_type": item["content_type"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
            }
            for item in message["attachments"]
        ]
        actual_attachment_summaries = sent.get("attachments", [])
        if actual_attachment_summaries != expected_attachment_summaries:
            result["state"] = "needs_reconciliation"
            result["error_type"] = "attachment_receipt_mismatch"
            _atomic_result(result_path, result)
            raise SafetyStop("send attachment receipt is uncertain; do not retry")
        record = {
            "stage": message["stage"],
            "subject": message["subject"],
            "message_id": message_id,
            "thread_id": thread_id,
            "attachments": [
                {
                    "filename": item["filename"],
                    "content_type": item["content_type"],
                    "bytes": item["bytes"],
                }
                for item in message["attachments"]
            ],
        }
        result["messages"].append(record)
        _atomic_result(result_path, result)
        try:
            _revalidate_send_inputs(manifest, message)
        except Exception as exc:
            result["state"] = "needs_reconciliation"
            result["error_type"] = _failure_type(exc)
            _atomic_result(result_path, result)
            if isinstance(exc, SafetyStop):
                raise
            raise SafetyStop("send inputs changed; do not retry") from exc
        result["completed_stages"].append(message["stage"])
        result["in_flight_stage"] = None
        result["attempt_started"] = False
        result.pop("error_type", None)
        _atomic_result(result_path, result)

    query = (
        f"in:sent to:{TEST_RECIPIENT} subject:{manifest['run_id']} newer_than:1d"
    )
    expected_by_id = {item["message_id"]: item for item in result["messages"]}
    try:
        search = process(
            [*common, "search", "--query", query, "--max-results", "10"], timeout
        )
    except Exception as exc:
        result["sent_verification"] = {
            "query": query,
            "sent_message_ids": list(expected_by_id),
            "verified_message_ids": [],
            "expected_count": 4,
        }
        result["state"] = "needs_reconciliation"
        result["error_type"] = _failure_type(exc)
        _atomic_result(result_path, result)
        raise SafetyStop("Sent verification failed; do not resend") from exc
    if not isinstance(search, dict):
        search = {}
    found = search.get("messages")
    ids = [
        item.get("message_id") for item in found
        if isinstance(item, dict) and isinstance(item.get("message_id"), str)
    ] if isinstance(found, list) else []
    verification_ok = len(ids) == 4 and len(set(ids)) == 4 and set(ids) == set(expected_by_id)
    verified_ids: list[str] = []
    if verification_ok:
        for message_id in ids:
            try:
                detail = process(
                    [*common, "read", "--message-id", message_id], timeout
                )
            except Exception as exc:
                result["sent_verification"] = {
                    "query": query,
                    "sent_message_ids": list(expected_by_id),
                    "verified_message_ids": verified_ids,
                    "expected_count": 4,
                }
                result["state"] = "needs_reconciliation"
                result["error_type"] = _failure_type(exc)
                _atomic_result(result_path, result)
                raise SafetyStop("Sent verification failed; do not resend") from exc
            if not isinstance(detail, dict):
                verification_ok = False
                break
            expected = expected_by_id[message_id]
            if (
                detail.get("message_id") != message_id
                or detail.get("from") != EXPECTED_SENDER
                or detail.get("to") != [TEST_RECIPIENT]
                or detail.get("cc") != []
                or detail.get("bcc") != []
                or detail.get("subject") != expected["subject"]
                or detail.get("attachments") != expected["attachments"]
            ):
                verification_ok = False
                break
            verified_ids.append(message_id)
    result["sent_verification"] = {
        "query": query,
        "sent_message_ids": list(expected_by_id),
        "verified_message_ids": verified_ids,
        "expected_count": 4,
    }
    result["state"] = "verified" if verification_ok else "needs_reconciliation"
    result["in_flight_stage"] = None
    result["attempt_started"] = False
    _atomic_result(result_path, result)
    if not verification_ok:
        raise SafetyStop("Sent verification is incomplete; do not resend")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the locked four-stage Gmail test.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gmail-cli", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_test(
            args.manifest, cli=args.gmail_cli, credentials=args.credentials,
            token=args.token, confirm=args.confirm, timeout=args.timeout,
        )
    except SafetyStop as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
