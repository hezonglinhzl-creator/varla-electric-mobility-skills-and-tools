"""Extract the current external message from Gmail-style quoted replies."""

from __future__ import annotations

from html.parser import HTMLParser
import re


_QUOTE_BOUNDARIES = (
    re.compile(r"(?im)^[ \t]*On .{1,500}?wrote:[ \t]*$"),
    re.compile(
        r"(?i)<[^<>\r\n]+@[^<>\r\n]+>\s*"
        r"(?:于|在).{0,160}?(?:写道|寫道)[:：]"
    ),
    re.compile(r"(?im)^[ \t]*(?:From|发件人|寄件者)\s*[:：].+$"),
    re.compile(r"(?is)<blockquote\b"),
)


class _PlainTextHTMLParser(HTMLParser):
    _BLOCK_TAGS = frozenset({"br", "div", "p", "li", "tr", "section"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0
        self.link_stack: list[str | None] = []

    def _newline(self) -> None:
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        lowered = tag.casefold()
        if lowered in {"head", "style", "script"}:
            self.hidden_depth += 1
            return
        if self.hidden_depth:
            return
        if lowered in self._BLOCK_TAGS:
            self._newline()
        if lowered == "a":
            self.link_stack.append(dict(attrs).get("href"))

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"head", "style", "script"} and self.hidden_depth:
            self.hidden_depth -= 1
            return
        if self.hidden_depth:
            return
        if lowered == "a" and self.link_stack:
            href = self.link_stack.pop()
            if isinstance(href, str) and href.startswith(("http://", "https://")):
                self.parts.append(f" <{href}>")
        if lowered in self._BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts).replace("\r", "")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.split("\n")]
        return "\n".join(line for line in lines if line).strip()


def _html_to_text(value: str) -> str:
    if not re.search(r"(?i)<(?:html|body|div|p|br|blockquote|a)\b", value):
        return value
    parser = _PlainTextHTMLParser()
    parser.feed(value)
    parser.close()
    return parser.text()


def latest_message_text(value: str) -> str:
    """Return only the new reply text while retaining the full text elsewhere."""
    if not isinstance(value, str):
        return ""
    normalized = value.replace("\r", "")
    end = len(normalized)
    for pattern in _QUOTE_BOUNDARIES:
        match = pattern.search(normalized)
        if match is not None:
            end = min(end, match.start())
    current = _html_to_text(normalized[:end]).replace("\r", "")
    plain_end = len(current)
    for pattern in _QUOTE_BOUNDARIES:
        match = pattern.search(current)
        if match is not None:
            plain_end = min(plain_end, match.start())
    current = current[:plain_end]
    current = "\n".join(
        line for line in current.splitlines() if not line.lstrip().startswith(">")
    )
    return current.strip()


__all__ = ["latest_message_text"]
