from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import hashlib
from pathlib import Path
from typing import Any, Iterator, Sequence


DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
ATTACHMENT_CONTENT_TYPES = {
    ".docx": DOCX_CONTENT_TYPE,
    ".pdf": "application/pdf",
}
MAX_ATTACHMENT_COUNT = 4
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_TOTAL_BYTES = 18 * 1024 * 1024


class SafetyError(RuntimeError):
    """A local safety guard stopped an operation before mutation."""


@dataclass(frozen=True)
class PreparedAttachment:
    payload: bytes
    metadata: dict[str, Any]

    def __iter__(self) -> Iterator[object]:
        yield self.payload
        yield self.metadata


def prepare_attachments(
    attachments: Sequence[Path],
    *,
    error_type: type[RuntimeError] = SafetyError,
) -> list[PreparedAttachment]:
    if len(attachments) > MAX_ATTACHMENT_COUNT:
        raise error_type("Stopped: at most 4 attachments are allowed.")
    prepared: list[PreparedAttachment] = []
    total_bytes = 0
    for supplied_path in attachments:
        path = Path(supplied_path)
        try:
            resolved = path.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise error_type(
                "Stopped: attachment does not exist or cannot be read."
            ) from exc
        if not resolved.is_file():
            raise error_type("Stopped: attachment must be a regular file.")
        content_type = ATTACHMENT_CONTENT_TYPES.get(resolved.suffix.lower())
        if content_type is None:
            raise error_type("Stopped: attachment must be a DOCX or PDF file.")
        try:
            payload = resolved.read_bytes()
        except OSError as exc:
            raise error_type("Stopped: attachment cannot be read.") from exc
        size = len(payload)
        if size == 0:
            raise error_type("Stopped: attachment must not be empty.")
        if size > MAX_ATTACHMENT_BYTES:
            raise error_type("Stopped: each attachment must be at most 10 MiB.")
        total_bytes += size
        if total_bytes > MAX_ATTACHMENTS_TOTAL_BYTES:
            raise error_type("Stopped: attachments must total at most 18 MiB.")
        prepared.append(
            PreparedAttachment(
                payload,
                {
                    "filename": resolved.name,
                    "bytes": size,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "content_type": content_type,
                },
            )
        )
    return prepared


def add_prepared_attachments(
    message: EmailMessage,
    prepared: Sequence[PreparedAttachment],
) -> None:
    for item in prepared:
        maintype, subtype = item.metadata["content_type"].split("/", 1)
        message.add_attachment(
            item.payload,
            maintype=maintype,
            subtype=subtype,
            filename=item.metadata["filename"],
        )
