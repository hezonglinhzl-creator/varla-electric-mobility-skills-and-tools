"""Low-frequency Feishu knowledge synchronization with local fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any, Callable
from uuid import uuid4

from app.gmail_gateway import sanitize_error as _gateway_sanitize_error


FEISHU_WIKI_URL = (
    "https://m9kzgsiucj.feishu.cn/wiki/"
    "Oo35w9AWgiy0m2kEB5jcUeC6nI3?from=from_copylink"
)
SYNC_INTERVAL = timedelta(hours=72)
COMMAND_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, slots=True)
class SyncResult:
    status: str
    using_local_cache: bool
    last_check: str | None = None
    last_success: str | None = None
    revision: str | None = None
    content_hash: str | None = None
    error: str | None = None
    active_path: str | None = None


Runner = Callable[..., Any]
Which = Callable[[str], str | None]
Clock = Callable[[], datetime]

_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _sanitize_error(error: BaseException | str) -> str:
    """Use the shared subprocess redactor for every persisted Feishu error."""
    message = _gateway_sanitize_error(error)
    if message == "Gmail command failed.":
        return "Feishu synchronization failed."
    return message[:500]


class _SyncGuard:
    """Non-blocking same-process and cross-process synchronization guard."""

    def __init__(self, state_path: Path) -> None:
        key = str(state_path.resolve())
        with _THREAD_LOCKS_GUARD:
            self._thread_lock = _THREAD_LOCKS.setdefault(key, threading.Lock())
        self._lock_path = state_path.with_name(f".{state_path.name}.lock")
        self._file: Any = None
        self._file_locked = False

    def acquire(self, timeout_seconds: float = COMMAND_TIMEOUT_SECONDS) -> bool:
        deadline = time.monotonic() + max(timeout_seconds, 0.0)
        if not self._thread_lock.acquire(timeout=max(timeout_seconds, 0.0)):
            return False
        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self._lock_path.open("a+b")
            self._file.seek(0, os.SEEK_END)
            if self._file.tell() == 0:
                self._file.write(b"\0")
                self._file.flush()
            while True:
                try:
                    self._file.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(
                            self._file.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )
                    else:
                        import fcntl

                        fcntl.flock(
                            self._file.fileno(),
                            fcntl.LOCK_EX | fcntl.LOCK_NB,
                        )
                    self._file_locked = True
                    return True
                except (OSError, BlockingIOError):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(0.05, remaining))
        except OSError:
            pass

        if not self._file_locked:
            if self._file is not None:
                self._file.close()
                self._file = None
            self._thread_lock.release()
            return False
        return True

    def release(self) -> None:
        try:
            if self._file_locked and self._file is not None:
                self._file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            if self._file is not None:
                self._file.close()
                self._file = None
            self._file_locked = False
            self._thread_lock.release()


class FeishuSyncer:
    """Synchronize the Feishu knowledge source without blocking local reads."""

    def __init__(
        self,
        *,
        state_path: str | Path,
        local_cache: str | Path,
        runner: Runner | None = None,
        rebuilder: Callable[[list[dict[str, Any]], Path], Any] | None = None,
        validator: Callable[[Path], Any] | None = None,
        which: Which | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.state_path = Path(state_path)
        self.local_cache = Path(local_cache)
        self.runner = runner or subprocess.run
        self.rebuilder = rebuilder
        self.validator = validator
        self.which = which or shutil.which
        self.clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            raise ValueError("clock must return a timezone-aware UTC datetime")
        return value.astimezone(UTC)

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds")

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(
            f".{self.state_path.name}.{uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)

    def record_success(
        self,
        when: datetime,
        revision: str,
        content_hash: str | None = None,
    ) -> None:
        timestamp = self._timestamp(when)
        state = self._load_state()
        state.update(
            {
                "last_check": timestamp,
                "last_success": timestamp,
                "revision": str(revision),
                "content_hash": content_hash,
                "error": None,
            }
        )
        self._save_state(state)

    def _result(
        self,
        status: str,
        state: dict[str, Any],
        *,
        using_local_cache: bool = True,
    ) -> SyncResult:
        return SyncResult(
            status=status,
            using_local_cache=using_local_cache,
            last_check=state.get("last_check"),
            last_success=state.get("last_success"),
            revision=state.get("revision"),
            content_hash=state.get("content_hash"),
            error=state.get("error"),
            active_path=state.get("active_path") or str(self.local_cache),
        )

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError:
            return None
        if timestamp.tzinfo is None:
            return None
        return timestamp.astimezone(UTC)

    def _is_due(self, state: dict[str, Any], now: datetime) -> bool:
        last_check = self._parse_timestamp(state.get("last_check"))
        return last_check is None or now - last_check >= SYNC_INTERVAL

    @staticmethod
    def _success_marker(state: dict[str, Any]) -> tuple[object, ...]:
        return (
            state.get("last_success"),
            state.get("revision"),
            state.get("content_hash"),
            state.get("active_path"),
        )

    def _run_json(self, argv: list[str]) -> dict[str, Any]:
        completed = self.runner(
            argv,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
        if getattr(completed, "returncode", 1) != 0:
            detail = _sanitize_error(getattr(completed, "stderr", ""))
            raise RuntimeError(
                f"lark-cli command failed with exit "
                f"{getattr(completed, 'returncode', 'unknown')}: {detail}"
            )
        try:
            payload = json.loads(getattr(completed, "stdout", ""))
        except json.JSONDecodeError as exc:
            raise RuntimeError("lark-cli returned invalid JSON") from exc
        if not isinstance(payload, dict) or payload.get("ok") is False:
            raise RuntimeError("lark-cli returned an unsuccessful response")
        return payload

    @staticmethod
    def _document(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        document = data.get("document") if isinstance(data, dict) else None
        if not isinstance(document, dict):
            raise RuntimeError("lark-cli response is missing document data")
        return document

    def check(self, *, force: bool = False) -> SyncResult:
        initial_state = self._load_state()
        now = self._now()
        if not force and not self._is_due(initial_state, now):
            return self._result("not_due", initial_state)

        guard = _SyncGuard(self.state_path)
        if not guard.acquire():
            return self._result("busy", initial_state)
        try:
            state = self._load_state()
            if not force and not self._is_due(state, now):
                return self._result("not_due", state)
            if (
                force
                and self._success_marker(state)
                != self._success_marker(initial_state)
                and state.get("last_success") is not None
                and state.get("error") is None
            ):
                return self._result("unchanged", state)
            return self._check_due(state, now)
        except Exception as exc:
            state.update(
                {
                    "last_check": self._timestamp(now),
                    "error": _sanitize_error(exc),
                }
            )
            try:
                self._save_state(state)
            except OSError:
                state["error"] = (
                    "local synchronization state could not be persisted"
                )
            return self._result("error", state)
        finally:
            guard.release()

    def _check_due(
        self,
        state: dict[str, Any],
        now: datetime,
    ) -> SyncResult:
        executable = self.which("lark-cli")
        if executable is None:
            state.update(
                {
                    "last_check": self._timestamp(now),
                    "error": (
                        "lark-cli is unavailable; using the last local cache"
                    ),
                }
            )
            self._save_state(state)
            return self._result("unavailable", state)

        outline_argv = [
            executable,
            "docs",
            "+fetch",
            "--doc",
            FEISHU_WIKI_URL,
            "--scope",
            "outline",
            "--max-depth",
            "1",
            "--as",
            "user",
        ]
        try:
            document = self._document(self._run_json(outline_argv))
        except Exception as exc:
            state.update(
                {
                    "last_check": self._timestamp(now),
                    "error": _sanitize_error(exc),
                }
            )
            self._save_state(state)
            return self._result("error", state)

        revision_value = document.get("revision_id")
        revision = None if revision_value is None else str(revision_value)
        content = document.get("content")
        if revision is None or not isinstance(content, str):
            state.update(
                {
                    "last_check": self._timestamp(now),
                    "error": "lark-cli response lacks revision or outline content",
                }
            )
            self._save_state(state)
            return self._result("error", state)

        content_hash = self.hash_content(content)
        if (
            state.get("revision") == revision
            and state.get("content_hash") == content_hash
        ):
            timestamp = self._timestamp(now)
            state.update(
                {
                    "last_check": timestamp,
                    "last_success": timestamp,
                    "revision": revision,
                    "content_hash": content_hash,
                    "error": None,
                }
            )
            self._save_state(state)
            return self._result("unchanged", state)

        return self._rebuild_changed(
            state=state,
            now=now,
            executable=executable,
            revision=revision,
            content_hash=content_hash,
            outline_content=content,
        )

    @staticmethod
    def _section_ids(outline_content: str) -> list[str]:
        matches = re.findall(
            r"<h1\b[^>]*\bid=[\"']([^\"']+)[\"']",
            outline_content,
            flags=re.IGNORECASE,
        )
        return list(dict.fromkeys(matches))

    def _rebuild_changed(
        self,
        *,
        state: dict[str, Any],
        now: datetime,
        executable: str,
        revision: str,
        content_hash: str,
        outline_content: str,
    ) -> SyncResult:
        if self.rebuilder is None or self.validator is None:
            raise RuntimeError(
                "knowledge changed but rebuilder or validator is unavailable"
            )
        section_ids = self._section_ids(outline_content)
        if not section_ids:
            raise RuntimeError(
                "changed Feishu outline contains no top-level section identifiers"
            )

        sections: list[dict[str, Any]] = []
        for section_id in section_ids:
            section_argv = [
                executable,
                "docs",
                "+fetch",
                "--doc",
                FEISHU_WIKI_URL,
                "--scope",
                "section",
                "--start-block-id",
                section_id,
                "--as",
                "user",
            ]
            section_document = self._document(self._run_json(section_argv))
            section_revision = section_document.get("revision_id")
            if (
                section_revision is not None
                and str(section_revision) != revision
            ):
                raise RuntimeError(
                    "Feishu revision changed while sections were being fetched"
                )
            section_content = section_document.get("content")
            if not isinstance(section_content, str):
                raise RuntimeError(
                    "lark-cli section response is missing document content"
                )
            sections.append(
                {
                    "block_id": section_id,
                    "revision": revision,
                    "content": section_content,
                }
            )

        staging = self.state_path.parent / (
            f".feishu-staging-{uuid4().hex}"
        )
        staging.mkdir(parents=True, exist_ok=False)
        self.rebuilder(sections, staging)
        validation_result = self.validator(staging)
        if validation_result is False:
            raise RuntimeError("staged Feishu knowledge package failed validation")

        generations = self.state_path.parent / "feishu-generations"
        generations.mkdir(parents=True, exist_ok=True)
        generation_name = (
            f"{now.strftime('%Y%m%dT%H%M%SZ')}-"
            f"{content_hash[:12]}-{uuid4().hex[:8]}"
        )
        generation = generations / generation_name
        os.replace(staging, generation)

        timestamp = self._timestamp(now)
        previous_state = dict(state)
        activated_state = dict(previous_state)
        activated_state.update(
            {
                "last_check": timestamp,
                "last_success": timestamp,
                "revision": revision,
                "content_hash": content_hash,
                "error": None,
                "active_path": str(generation.resolve()),
            }
        )
        try:
            self._save_state(activated_state)
        except OSError as exc:
            fallback_state = dict(previous_state)
            fallback_state.update(
                {
                    "last_check": timestamp,
                    "error": (
                        "new Feishu generation was not activated because "
                        f"local state persistence failed: {_sanitize_error(exc)}"
                    ),
                }
            )
            self._save_state(fallback_state)
            state.clear()
            state.update(fallback_state)
            return self._result("error", state)

        state.clear()
        state.update(activated_state)
        return self._result("updated", state, using_local_cache=False)
