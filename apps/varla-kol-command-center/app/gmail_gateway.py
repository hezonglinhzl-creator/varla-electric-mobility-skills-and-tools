"""Safe subprocess boundary for the installed Varla Gmail CLI."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


FORWARD_RECIPIENTS = frozenset(
    {"support@varlascooter.com", "customer@varlascooter.com"}
)
EXPECTED_ACCOUNT = "info@varlascooter.com"
_PEM_PRIVATE_KEY = re.compile(
    r"""(?isx)
    -----BEGIN[ ](?P<label>[A-Z0-9 ]*PRIVATE[ ]KEY)-----
    .*?
    -----END[ ](?P=label)-----
    """
)
_QUOTED_PRIVATE_PATH = re.compile(
    r"""(?ix)
    (?P<quote>["'])
    (?P<value>
        (?:
            [a-z]:[\\/]
            |
            \\\\
            |
            //[a-z0-9_-]+/
            |
            /(?:home|users)/
            |
            ~[\\/]\.(?:config|ssh|aws|gnupg|kube)(?:[\\/]|$)
        )
        [^\r\n]*?
    )
    (?P=quote)
    """
)
_HTTP_URL = re.compile(r"""(?i)https?://[^\s"'<>]+""")
_KNOWN_PATH_FILE_END = re.compile(
    r"""(?ix)
    \.(?:json|pem|key|db|txt|yaml|yml)
    (?=$|[\s;,\)\]\}])
    """
)
_UNSAFE_PATH_FOLLOWING = re.compile(
    r"""(?ix)
    \s+
    (?:
        documentation\s*:
        |
        error\s*:
        |
        https?://
    )
    """
)
_PATH_BOUNDARY = re.compile(r"[\r\n;,\)\]\}]")
_UNQUOTED_PRIVATE_STARTS = (
    re.compile(r"(?i)(?<![a-z0-9])[a-z]:[\\/]"),
    re.compile(r"(?<!\\)\\\\"),
    re.compile(r"(?i)(?<![:/])//(?=[a-z0-9_-]+/)"),
    re.compile(r"(?i)(?<![a-z0-9:/])/(?:home|users)/"),
    re.compile(
        r"(?i)(?<![a-z0-9/])~[\\/]"
        r"(?=\.(?:config|ssh|aws|gnupg|kube)(?:[\\/]|$))"
    ),
)
_SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?P<prefix>
        ["']?(?:access[_-]?token|refresh[_-]?token|token|credentials?|
        client[_-]?secret|app[_-]?secret|api[_-]?key|private[_-]?key|
        signing[_-]?secret|webhook[_-]?secret|access[_-]?key|password|
        secret)["']?\s*[:=]\s*
    )
    (?P<value>
        "(?:\\.|[^"])*" |
        '(?:\\.|[^'])*' |
        [^\s,}\]&]+
    )
    """
)
_AUTHORIZATION = re.compile(
    r"(?i)\b(?:authorization\s*:\s*)?(?:bearer|basic)\s+[a-z0-9._~+/=-]+"
)
_URL_QUERY_SECRET = re.compile(
    r"""(?ix)
    (?P<prefix>[?&](?:access[_-]?token|refresh[_-]?token|token|
    client[_-]?secret|app[_-]?secret|api[_-]?key|private[_-]?key|
    signing[_-]?secret|webhook[_-]?secret|access[_-]?key|password|
    secret|credentials?)=)
    [^&#\s"']*
    """
)


def _redact_quoted_private_paths(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return f"{quote}[REDACTED_PATH]{quote}"

    return _QUOTED_PRIVATE_PATH.sub(replace, text)


def _inside_http_url(text: str, position: int) -> bool:
    return any(
        match.start() <= position < match.end()
        for match in _HTTP_URL.finditer(text)
    )


def _next_private_path_start(
    text: str,
    cursor: int,
) -> re.Match[str] | None:
    matches = [
        match
        for pattern in _UNQUOTED_PRIVATE_STARTS
        if (match := pattern.search(text, cursor)) is not None
        and not _inside_http_url(text, match.start())
    ]
    return min(matches, key=lambda match: match.start(), default=None)


def _safe_unquoted_path_end(text: str, start: int) -> int | None:
    tail = text[start:]
    safe_candidates: list[int] = []
    if extension := _KNOWN_PATH_FILE_END.search(tail):
        safe_candidates.append(extension.end())
    if boundary := _PATH_BOUNDARY.search(tail):
        safe_candidates.append(boundary.start())

    if safe_candidates:
        safe_end = min(safe_candidates)
        unsafe = _UNSAFE_PATH_FOLLOWING.search(tail)
        if unsafe is not None and unsafe.start() < safe_end:
            return None
        return start + safe_end

    if not any(character.isspace() for character in tail):
        return len(text)
    return None


def _redact_private_paths(text: str) -> str:
    text = _redact_quoted_private_paths(text)
    cursor = 0
    while match := _next_private_path_start(text, cursor):
        start = match.start()
        end = _safe_unquoted_path_end(text, start)
        if end is None:
            return "[REDACTED_ERROR]"
        text = f"{text[:start]}[REDACTED_PATH]{text[end:]}"
        cursor = start + len("[REDACTED_PATH]")
    return text


def _safe_error(value: object, protected_paths: Sequence[Path] = ()) -> str:
    """Return a short error message without credentials or local paths."""

    text = str(value or "").strip()
    for path in protected_paths:
        candidates = {
            str(path),
            str(path).replace("\\", "/"),
            str(path).replace("/", "\\"),
            path.name,
        }
        for candidate in sorted(candidates, key=len, reverse=True):
            if candidate:
                text = re.sub(re.escape(candidate), "[REDACTED]", text, flags=re.I)
    text = _PEM_PRIVATE_KEY.sub("[REDACTED_SECRET]", text)
    text = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]", text
    )
    text = _AUTHORIZATION.sub("Authorization: [REDACTED]", text)
    text = _URL_QUERY_SECRET.sub(
        lambda match: f"{match.group('prefix')}[REDACTED]", text
    )
    text = _redact_private_paths(text)
    return text[:1000] or "Gmail command failed."


class GatewayError(RuntimeError):
    """A user-safe failure returned by the Gmail subprocess boundary."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        retryable: bool = False,
        delivery_unknown: bool = False,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.retryable = retryable
        self.delivery_unknown = delivery_unknown


class GmailGateway:
    """Invoke the installed Gmail automation script without a command shell."""

    def __init__(
        self,
        *,
        python_executable: str | Path,
        script_path: str | Path,
        credentials_path: str | Path,
        token_path: str | Path,
        expected_account: str = "info@varlascooter.com",
        runner: Callable[..., object] = subprocess.run,
        timeout_seconds: int = 30,
    ) -> None:
        if expected_account != EXPECTED_ACCOUNT:
            raise ValueError(
                "expected_account must be exactly info@varlascooter.com"
            )
        self._python_executable = Path(python_executable)
        self._script_path = Path(script_path)
        self._credentials_path = Path(credentials_path)
        self._token_path = Path(token_path)
        self._expected_account = expected_account
        self._runner = runner
        self._timeout_seconds = min(max(int(timeout_seconds), 1), 30)

    @property
    def _protected_paths(self) -> tuple[Path, ...]:
        return (
            self._python_executable,
            self._script_path,
            self._credentials_path,
            self._token_path,
        )

    def _base_command(self) -> list[str]:
        command = [
            str(self._python_executable),
            str(self._script_path),
            "--credentials",
            str(self._credentials_path),
            "--token",
            str(self._token_path),
        ]
        command.extend(["--expected-account", self._expected_account])
        return command

    def _execute(self, arguments: Sequence[str]) -> dict[str, Any]:
        command = [*self._base_command(), *[str(item) for item in arguments]]
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=self._timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GatewayError(
                "timeout",
                "Gmail command timed out after 30 seconds.",
                retryable=False,
                delivery_unknown=True,
            ) from exc
        except OSError as exc:
            raise GatewayError(
                "launch_failed",
                _safe_error(exc, self._protected_paths),
                retryable=True,
            ) from exc

        returncode = getattr(completed, "returncode", None)
        stdout = getattr(completed, "stdout", "")
        stderr = getattr(completed, "stderr", "")
        try:
            parsed = json.loads(stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            if returncode != 0:
                raise GatewayError(
                    "command_failed",
                    _safe_error(stderr or stdout, self._protected_paths),
                    retryable=True,
                ) from exc
            raise GatewayError(
                "invalid_json",
                _safe_error(stdout, self._protected_paths),
            ) from exc
        if not isinstance(parsed, dict):
            raise GatewayError(
                "invalid_json",
                "Gmail command returned a non-object JSON response.",
            )
        if parsed.get("status") == "error":
            error = parsed.get("error")
            error = error if isinstance(error, Mapping) else {}
            code = error.get("code")
            detail = error.get("message") or error.get("detail") or "Gmail command failed."
            if (
                code == "stopped"
                and isinstance(detail, str)
                and "dependencies are not installed" in detail.lower()
            ):
                code = "dependency_missing"
            retryable = error.get("retryable") is True
            http_status = error.get("http_status")
            delivery_unknown = not (
                isinstance(http_status, int) and 400 <= http_status < 500
            ) and code == "gmail_api_error"
            raise GatewayError(
                str(code) if isinstance(code, str) and code else "command_error",
                _safe_error(detail, self._protected_paths),
                retryable=(
                    retryable
                    or code == "stopped"
                    or (
                        isinstance(http_status, int)
                        and 400 <= http_status < 500
                    )
                ),
                delivery_unknown=delivery_unknown,
            )
        if returncode != 0:
            raise GatewayError(
                "command_failed",
                _safe_error(stderr or stdout, self._protected_paths),
                retryable=True,
            )
        return parsed

    def thread_read(self, thread_id: str) -> dict[str, Any]:
        return self._execute(["thread-read", "--thread-id", thread_id])

    def search(self, query: str, *, max_results: int = 10) -> dict[str, Any]:
        if (
            not isinstance(query, str)
            or not query.strip()
            or "\r" in query
            or "\n" in query
        ):
            raise ValueError("query must be a non-empty single-line string")
        if (
            not isinstance(max_results, int)
            or isinstance(max_results, bool)
            or not 1 <= max_results <= 50
        ):
            raise ValueError("max_results must be between 1 and 50")
        return self._execute(
            [
                "search",
                "--query",
                query.strip(),
                "--max-results",
                str(max_results),
            ]
        )

    def label_add(self, thread_id: str) -> dict[str, Any]:
        """Add the one approved existing label; the CLI refuses creation."""

        return self._execute(
            ["label-add", "--thread-id", thread_id, "--label", "KOL"]
        )

    def mark_spam(
        self,
        thread_id: str,
        source_message_id: str,
        sender: str,
    ) -> dict[str, Any]:
        """Move one exact, preclassified vendor thread to recoverable Spam."""

        return self._execute(
            [
                "spam",
                "--thread-id",
                thread_id,
                "--message-id",
                source_message_id,
                "--sender",
                sender,
                "--confirm",
                "SPAM",
            ]
        )

    def move_to_trash(
        self,
        thread_id: str,
        source_message_id: str,
        sender: str,
    ) -> dict[str, Any]:
        """Move one exact, preclassified vendor thread to recoverable Trash."""

        return self._execute(
            [
                "trash",
                "--thread-id",
                thread_id,
                "--message-id",
                source_message_id,
                "--sender",
                sender,
                "--confirm",
                "TRASH",
            ]
        )

    def ensure_sender_trash_filter(self, sender: str) -> dict[str, Any]:
        """Create or reuse one exact-sender Gmail filter for future Trash routing."""

        return self._execute(
            [
                "filter-block",
                "--sender",
                sender,
                "--confirm",
                "BLOCK",
            ]
        )

    def reply_send(self, message_id: str, body: str) -> dict[str, Any]:
        return self._execute(
            [
                "reply",
                "--message-id",
                message_id,
                "--body",
                body,
                "--mode",
                "send",
                "--confirm",
                "SEND",
            ]
        )

    def forward_send(
        self,
        message_id: str,
        recipient: str,
        body: str,
    ) -> dict[str, Any]:
        if recipient not in FORWARD_RECIPIENTS:
            raise GatewayError(
                "unsafe_recipient",
                "Forwarding is limited to the fixed Varla department addresses.",
            )
        return self._execute(
            [
                "forward",
                "--message-id",
                message_id,
                "--to",
                recipient,
                "--body",
                body,
                "--mode",
                "send",
                "--confirm",
                "SEND",
            ]
        )


sanitize_error = _safe_error


__all__ = [
    "FORWARD_RECIPIENTS",
    "GatewayError",
    "GmailGateway",
    "sanitize_error",
]
