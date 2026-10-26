"""Deterministic latest-message and stored-thread alignment evidence."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ContextAnalysis:
    latest_intents: tuple[str, ...]
    provided_facts: tuple[str, ...]
    missing_facts: tuple[str, ...]
    disposition: str | None


_DECLINE_RE = re.compile(
    r"not (?:the )?best fit|"
    r"focused on creators who already have a larger|"
    r"partnership spots are limited|"
    r"revisit (?:a |the )?(?:collaboration|conversation)|"
    r"hope to reconnect when the timing is right",
    re.I,
)
_SHIPPING_RE = re.compile(
    r"\b(?:ship|ships|shipped|shipping|shipment|tracking|delivery|carrier)\b|"
    r"发货|物流|追踪|到货",
    re.I,
)
_PERFORMANCE_RE = re.compile(
    r"\b(?:sold|sales|revenue|views?|viewers?|analytics?|conversions?)\b|"
    r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:k|m)?\s+(?:views?|followers?)\b",
    re.I,
)
_CLOSING_RE = re.compile(
    r"\b(?:thanks?|thank you).{0,120}"
    r"(?:your time|future|understand|response|opportunity)\b|"
    r"\bhope to collaborate.{0,50}\bfuture\b",
    re.I | re.S,
)
_CONTRACT_RE = re.compile(r"\b(?:contract|agreement|sign(?:ed|ature)?)\b", re.I)
_COMMISSION_RE = re.compile(
    r"\b(?:commission|affiliate|percentage|rate|coupon|discount code)\b",
    re.I,
)
_URL_RE = r"https?://[^\s<>\]\[\)\(]+"


def _has_platform_handle(text: str, platform: str) -> bool:
    aliases = {
        "youtube": r"(?:youtube|yt)",
        "tiktok": r"tiktok",
        "instagram": r"(?:instagram|ig)",
    }[platform]
    descriptor = r"(?:\s+(?:account|handle|username|channel)|账号|帳號)?"
    separator = r"(?:\s*(?::|-|=|\bis\b|是)\s*)"
    return bool(
        re.search(
            rf"\b{aliases}{descriptor}\s*\(\s*@[a-z0-9_.-]+\s*\)",
            text,
            re.I,
        )
        or re.search(
            rf"\b{aliases}{descriptor}{separator}@?[a-z0-9_.-]+",
            text,
            re.I,
        )
        or re.search(rf"\b{aliases}{descriptor}\s+@[a-z0-9_.-]+", text, re.I)
    )


def _provided_facts(text: str) -> set[str]:
    facts: set[str] = set()
    urls = re.findall(_URL_RE, text, re.I)
    lowered_urls = [url.casefold() for url in urls]
    if any("youtu" in url for url in lowered_urls):
        facts.add("youtube_link")
    if _has_platform_handle(text, "youtube"):
        facts.add("youtube_link")
    if any("tiktok" in url for url in lowered_urls):
        facts.add("tiktok_link")
    if _has_platform_handle(text, "tiktok"):
        facts.add("tiktok_link")
    if any("instagram" in url or "instagr.am" in url for url in lowered_urls):
        facts.add("instagram_link")
    if _has_platform_handle(text, "instagram"):
        facts.add("instagram_link")
    if re.search(r"\bUGC\b|\buser[- ]generated content\b", text, re.I):
        facts.add("ugc_creator")
    quantified = bool(
        re.search(r"(?:\$\s*)?\b\d[\d,.]*(?:\s*[kKmM%])?\b", text)
    )
    if quantified and _PERFORMANCE_RE.search(text):
        facts.add("performance_metrics")
    if (
        quantified
        and re.search(r"\b(?:audience|demographic|followers?)\b", text, re.I)
    ) or re.search(
        r"\btop countr(?:y|ies)\s*(?:are|include|:)", text, re.I
    ):
        facts.add("audience_information")
    if re.search(r"\b(?:signed|completed|attached)\b.{0,50}\b(?:contract|agreement)\b", text, re.I | re.S):
        facts.add("signed_contract")
    return facts


def requested_facts(latest: str) -> set[str]:
    request = re.search(
        r"\b(?:send|share|provide|need|request|could you|please)\b",
        latest,
        re.I,
    )
    if not request:
        return set()
    requested: set[str] = set()

    def platform_requested(platform: str) -> bool:
        return bool(
            re.search(
                rf"\b(?:send|share|provide|need|request|could you|please)\b"
                rf".{{0,200}}\b(?:{platform})\b",
                latest,
                re.I | re.S,
            )
            or re.search(
                rf"\b(?:{platform})\b.{{0,80}}\b(?:links?|accounts?|handles?)\b",
                latest,
                re.I | re.S,
            )
        )

    if platform_requested(r"youtube|yt"):
        requested.add("youtube_link")
    if platform_requested("tiktok"):
        requested.add("tiktok_link")
    if platform_requested(r"instagram|ig"):
        requested.add("instagram_link")
    if re.search(r"\b(?:audience|demographic|top countr(?:y|ies)|followers?)\b", latest, re.I):
        requested.add("audience_information")
    if re.search(r"\b(?:views?|sales|revenue|analytics?|performance)\b", latest, re.I):
        requested.add("performance_metrics")
    return requested


def _latest_intents(latest: str, disposition: str | None) -> tuple[str, ...]:
    intents: list[str] = []
    if disposition == "declined" and _CLOSING_RE.search(latest):
        return ("closing_acknowledgement",)
    if _PERFORMANCE_RE.search(latest):
        intents.append("performance_evidence")
    if _SHIPPING_RE.search(latest):
        intents.append("shipping")
    if _CONTRACT_RE.search(latest):
        intents.append("contract")
    if _COMMISSION_RE.search(latest):
        intents.append("commission")
    if not intents and re.search(r"\b(?:collab|collaboration|sponsor|creator)\b", latest, re.I):
        intents.append("collaboration")
    return tuple(dict.fromkeys(intents))


def analyze_context(
    latest_message: str,
    thread_context: str,
    *,
    creator_context: str | None = None,
) -> ContextAnalysis:
    """Analyze latest content first, using history only as constraints/facts."""
    latest = latest_message if isinstance(latest_message, str) else ""
    history = thread_context if isinstance(thread_context, str) else ""
    creator_history = (
        creator_context
        if isinstance(creator_context, str)
        else history
    )
    combined = f"{creator_history}\n{latest}"
    provided = _provided_facts(combined)
    requested = requested_facts(latest)
    disposition = "declined" if _DECLINE_RE.search(history) else None
    return ContextAnalysis(
        latest_intents=_latest_intents(latest, disposition),
        provided_facts=tuple(sorted(provided)),
        missing_facts=tuple(sorted(requested - provided)),
        disposition=disposition,
    )


__all__ = ["ContextAnalysis", "analyze_context", "requested_facts"]
