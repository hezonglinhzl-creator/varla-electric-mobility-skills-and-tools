"""Validation, canonicalization, and safe rendering for reply grounding."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, Sequence

from app.knowledge import KnowledgeHit


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_RFC_FIELD_LINE_RE = re.compile(
    r"^[ \t]*[\x21-\x39\x3b-\x7e]{1,997}:",
    re.MULTILINE,
)
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def is_safe_multiline_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and "\r" not in value
        and _CONTROL_RE.search(value) is None
        and _RFC_FIELD_LINE_RE.search(value) is None
    )


def is_safe_component(value: object) -> bool:
    return (
        is_safe_multiline_text(value)
        and "\n" not in value
        and bool(value.strip())
    )


def neutralize_header_lines(value: str) -> str:
    """Keep trusted labels readable without leaving RFC-shaped header lines."""

    lines: list[str] = []
    for line in value.split("\n"):
        match = _RFC_FIELD_LINE_RE.match(line)
        if match is not None:
            colon_index = match.end() - 1
            line = f"{line[:colon_index]}：{line[colon_index + 1:]}"
        lines.append(line)
    return "\n".join(lines)


def sanitize_variable(value: object) -> str:
    text = _CONTROL_RE.sub("", str(value))
    text = neutralize_header_lines(text.replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()[:200]
    return text


def stable_source_name(source: str) -> str:
    """Return a filename for Windows or POSIX paths without host-path leakage."""

    normalized = source.replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1]


def canonical_hit_key(hit: KnowledgeHit) -> tuple[str, ...]:
    return (
        hit.source.casefold(),
        hit.version.casefold(),
        hit.title.casefold(),
        hit.content_hash.casefold(),
        hit.content,
        hit.group,
    )


def validate_index_hit(
    hit: object,
    *,
    confirmed_group: str,
    index: object,
) -> KnowledgeHit | None:
    """Accept only safe hits verified by the active index/package manifest."""

    if not isinstance(hit, KnowledgeHit):
        return None
    string_values = (
        hit.group,
        hit.title,
        hit.content,
        hit.source,
        hit.version,
        hit.content_hash,
    )
    if not all(isinstance(value, str) for value in string_values):
        return None
    if (
        hit.group != confirmed_group
        or "\r" in hit.content
        or "\r" in hit.title
        or "\r" in hit.source
        or "\r" in hit.version
        or _CONTROL_RE.search(hit.content) is not None
        or _CONTROL_RE.search(hit.title) is not None
        or _CONTROL_RE.search(hit.source) is not None
        or _CONTROL_RE.search(hit.version) is not None
        or "\n" in hit.title
        or "\n" in hit.source
        or "\n" in hit.version
        or not _HEX_64_RE.fullmatch(hit.content_hash)
        or not isinstance(hit.score, (int, float))
        or isinstance(hit.score, bool)
        or not math.isfinite(float(hit.score))
    ):
        return None
    normalized_content = hit.content.strip()
    if (
        not normalized_content
        or normalized_content != hit.content
        or hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
        != hit.content_hash.casefold()
    ):
        return None
    verifier = getattr(index, "verify_hit", None)
    if not callable(verifier):
        return None
    try:
        if verifier(hit) is not True:
            return None
    except Exception:
        return None
    return KnowledgeHit(
        group=hit.group,
        title=hit.title,
        content=hit.content,
        source=stable_source_name(hit.source),
        version=hit.version,
        content_hash=hit.content_hash,
        score=hit.score,
    )


def canonicalize_sources(hits: Iterable[KnowledgeHit]) -> list[KnowledgeHit]:
    unique: dict[tuple[str, ...], KnowledgeHit] = {}
    for hit in hits:
        key = (
            hit.source,
            hit.version,
            hit.title,
            hit.content_hash,
            hit.content,
            hit.group,
        )
        existing = unique.get(key)
        if existing is None or hit.score < existing.score:
            unique[key] = hit
    return sorted(unique.values(), key=canonical_hit_key)


def citation(hit: KnowledgeHit) -> str:
    rendered_source = neutralize_header_lines(stable_source_name(hit.source))
    rendered_version = neutralize_header_lines(hit.version)
    if not (
        is_safe_component(rendered_source)
        and is_safe_component(rendered_version)
        and _HEX_64_RE.fullmatch(hit.content_hash)
    ):
        raise ValueError("unsafe citation metadata")
    return (
        f"[Source: {rendered_source} | Version: {rendered_version} | "
        f"SHA256: {hit.content_hash[:12]}]"
    )


_TRAILING_SIGNATURE_RE = re.compile(
    r"(?is)(?:^|\n\n)"
    r"(?:best(?:\s+regards)?|kind\s+regards|regards|sincerely|thank\s+you),?"
    r"[ \t]*\n[^\r\n]+(?:\n[^\r\n]+){0,2}[ \t]*$"
)

_LEADING_OPENING_RE = re.compile(
    r"(?i)^\s*(?:(?:hi|hello|hey|dear)\b|thanks\b|thank\s+you\b)"
)


def _has_trailing_signature(text: str) -> bool:
    return _TRAILING_SIGNATURE_RE.search(text) is not None


def _has_leading_opening(text: str) -> bool:
    return _LEADING_OPENING_RE.search(text) is not None


def build_variants(
    payload: str,
    sources: Sequence[KnowledgeHit],
) -> dict[str, list[str]]:
    rendered_payload = re.sub(
        r"(?im)^[ \t]*\[Source:[^\r\n]*\|\s*Version:[^\r\n]*\|\s*"
        r"SHA256:[0-9a-f]{12,64}\][ \t]*$",
        "",
        neutralize_header_lines(payload),
    )
    rendered_payload = re.sub(
        r"(?im)^[ \t]*Content SHA256:\s*[0-9a-f]{64}[ \t]*$",
        "",
        rendered_payload,
    ).strip()
    if not is_safe_multiline_text(rendered_payload):
        raise ValueError("unsafe reply payload")
    if _has_trailing_signature(rendered_payload):
        formal_variants = [rendered_payload, rendered_payload]
    else:
        formal_variants = [
            f"Hello,\n\n{rendered_payload}\n\nBest regards,\nVarla Team",
            f"Hello,\n\nThank you for contacting Varla. {rendered_payload}\n\n"
            f"Sincerely,\nVarla Team",
        ]
    natural_variants = (
        [rendered_payload, rendered_payload]
        if _has_leading_opening(rendered_payload)
        else [
            f"Thanks for reaching out. {rendered_payload}",
            f"Thanks for your message. {rendered_payload}",
        ]
    )
    return {
        "Natural": natural_variants,
        "Formal": formal_variants,
        "Short": [
            rendered_payload,
            f"Thanks — {rendered_payload}",
        ],
    }


def canonical_warnings(warnings: Iterable[str]) -> list[str]:
    safe = {
        warning.strip()
        for warning in warnings
        if is_safe_multiline_text(warning) and warning.strip()
    }
    return sorted(safe, key=str.casefold)
