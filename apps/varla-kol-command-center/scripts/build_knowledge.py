"""Build deterministic, group-scoped knowledge packages from the Varla DOCX."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile
from typing import Iterator

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


SOURCE_FILENAME = (
    "Varla_KOL_Reply_Playbook_v4.1_Commission_Products_Update_20260724.docx"
)
FORMAT_VERSION = "1"
GROUPS = ("kol", "pre-sales", "order-logistics", "after-sales")
DEPARTMENT_ROUTES = {
    "kol": {"gmail_label": "KOL", "department": None},
    "pre-sales": {"gmail_label": None, "department": "support@varlascooter.com"},
    "order-logistics": {
        "gmail_label": None,
        "department": "support@varlascooter.com",
    },
    "after-sales": {
        "gmail_label": None,
        "department": "customer@varlascooter.com",
    },
}
_SECTION_RE = re.compile(r"^\s*(\d+)(?:\.|\s)")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^;\n|]+")
SECTION_ROUTES = {
    1: "kol",
    2: "pre-sales",
    3: "kol",
    4: "kol",
    5: "kol",
    6: "kol",
    7: "kol",
    8: "kol",
    9: "kol",
    10: "order-logistics",
    11: "kol",
    12: "kol",
    13: "kol",
    14: "after-sales",
    15: "kol",
    16: "kol",
    17: "kol",
    18: "kol",
    19: "kol",
    20: "kol",
    21: "kol",
    22: "kol",
    23: "kol",
    24: "kol",
}
LEAF_ID_ROUTES = {
    "11.2": "order-logistics",
    "13.6": "kol",
    "15.1": "order-logistics",
    "15.4": "pre-sales",
    "h003": "order-logistics",
    "h004": "order-logistics",
    "h025": "order-logistics",
    "h029": "pre-sales",
    "19.10": "pre-sales",
    "20.4": "order-logistics",
    "20.9": "after-sales",
    "21.1": "order-logistics",
    "24.1": "kol",
    "24.2": "after-sales",
    "shipment-status": "order-logistics",
    "shipment_status": "order-logistics",
    "price_final_boundary": "pre-sales",
    "battery_life_question": "after-sales",
    "shipping_damage_claim": "after-sales",
    "return_label_question": "after-sales",
}
ROOT_PREFIX_ROUTES = {
    "appendix a:": "kol",
    "appendix b:": "kol",
    "v4.0 ": "kol",
    "v4.2 ": "kol",
}
ALLOWLISTED_HEADINGS = frozenset({"table of contents", "目录 / table of contents"})


@dataclass(frozen=True, slots=True)
class Chunk:
    heading: str
    heading_path: tuple[str, ...]
    heading_level: int
    content: str
    section: int | None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _stabilize_machine_paths(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw = match.group(0).strip()
        return PureWindowsPath(raw).name

    return _WINDOWS_ABSOLUTE_PATH_RE.sub(replace, value)


def locate_source(source_root: str | Path, filename: str = SOURCE_FILENAME) -> Path:
    """Locate exactly one exact filename using Path.rglob."""

    root = Path(source_root)
    matches = sorted(
        (path for path in root.rglob(filename) if path.is_file()),
        key=lambda path: str(path).casefold(),
    )
    if not matches:
        raise FileNotFoundError(f"{filename!r} was not found beneath {root}")
    if len(matches) > 1:
        raise ValueError(f"multiple exact source files found for {filename!r}")
    return matches[0]


def _iter_blocks(document: DocumentType) -> Iterator[Paragraph | Table]:
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _table_markdown(table: Table) -> str:
    rows = [[_clean(cell.text) for cell in row.cells] for row in table.rows]
    if not rows or not any(any(cell for cell in row) for row in rows):
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]

    def render(row: list[str]) -> str:
        escaped = [cell.replace("|", "\\|").replace("\n", "<br>") for cell in row]
        return "| " + " | ".join(escaped) + " |"

    return "\n".join(
        [render(padded[0]), "| " + " | ".join(["---"] * width) + " |"]
        + [render(row) for row in padded[1:]]
    )


def extract_chunks(document: DocumentType) -> list[Chunk]:
    """Extract content in document order and retain its heading hierarchy."""

    chunks: list[Chunk] = []
    heading_stack: dict[int, str] = {}
    current_heading = ""
    current_level = 0
    content_parts: list[str] = []

    def flush() -> None:
        if not current_heading:
            return
        content = _stabilize_machine_paths(
            "\n\n".join(part for part in content_parts if part).strip()
        )
        if not content:
            return
        heading_path = tuple(heading_stack[level] for level in sorted(heading_stack))
        section_match = _SECTION_RE.match(heading_path[0]) if heading_path else None
        chunks.append(
            Chunk(
                heading=current_heading,
                heading_path=heading_path,
                heading_level=current_level,
                content=content,
                section=int(section_match.group(1)) if section_match else None,
            )
        )

    for block in _iter_blocks(document):
        if isinstance(block, Paragraph):
            text = _clean(block.text)
            if not text:
                continue
            style = block.style.name if block.style is not None else ""
            heading_match = re.fullmatch(r"Heading\s+(\d+)", style)
            if heading_match:
                flush()
                content_parts = []
                current_heading = text
                current_level = int(heading_match.group(1))
                for level in tuple(heading_stack):
                    if level >= current_level:
                        del heading_stack[level]
                heading_stack[current_level] = text
            elif current_heading:
                content_parts.append(text)
        elif current_heading:
            table_text = _table_markdown(block)
            if table_text:
                content_parts.append(table_text)
    flush()
    return chunks


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _leaf_ids(heading: str) -> tuple[str, ...]:
    normalized = heading.casefold().strip()
    ids: list[str] = []
    numbered = re.match(r"^(\d+\.\d+)", normalized)
    if numbered:
        ids.append(numbered.group(1))
    historical = re.match(r"^(h\d+)", normalized)
    if historical:
        ids.append(historical.group(1))
    ids.extend(
        match.casefold()
        for match in re.findall(r"\(([a-z0-9_-]+)\)", normalized)
    )
    if re.fullmatch(r"[a-z0-9_-]+", normalized):
        ids.append(normalized)
    return tuple(dict.fromkeys(ids))


def route_chunk(chunk: Chunk) -> str | None:
    """Route using declarative IDs/sections, then narrow leaf-heading fallbacks."""

    heading = chunk.heading.casefold()
    root = chunk.heading_path[0].casefold() if chunk.heading_path else ""

    for leaf_id in _leaf_ids(chunk.heading):
        if leaf_id in LEAF_ID_ROUTES:
            return LEAF_ID_ROUTES[leaf_id]
    for prefix, group in ROOT_PREFIX_ROUTES.items():
        if root.startswith(prefix):
            named_ids = _leaf_ids(chunk.heading)
            if named_ids and named_ids[-1] in LEAF_ID_ROUTES:
                return LEAF_ID_ROUTES[named_ids[-1]]
            # Narrow leaf fallbacks below may override this broad module route.
            break

    if _contains_any(
        heading,
        (
            "after-sales",
            "after sales",
            "repair",
            "warranty",
            "refund",
            "return label",
            "return_label",
            "return shipping label",
            "damage",
            "factory inspection",
            "brake",
            "support escalation",
        ),
    ):
        return "after-sales"
    if "shipping cost" in heading:
        return "pre-sales"
    if _contains_any(
        heading,
        (
            "shipping",
            "tracking",
            "warehouse",
            "shipment",
            "order status",
            "delivery status",
            "delay",
            "ocean freight",
        ),
    ):
        return "order-logistics"
    if _contains_any(
        heading,
        (
            "price",
            " buy ",
            "buying",
            "purchase",
            "inventory",
            "product specs",
            "exact specs",
            "product canon",
            "official specs",
            "battery life",
        ),
    ):
        return "pre-sales"
    if chunk.section in SECTION_ROUTES:
        return SECTION_ROUTES[chunk.section]
    for prefix, group in ROOT_PREFIX_ROUTES.items():
        if root.startswith(prefix):
            return group
    return None


def _is_allowlisted(chunk: Chunk) -> bool:
    return chunk.heading.casefold().strip() in ALLOWLISTED_HEADINGS


def _normalize_header(header: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", header.casefold()).strip("_")
    aliases = {
        "product": "model",
        "official_price": "price",
        "top_speed": "top_speed",
        "controller_positioning": "controller_positioning",
    }
    return aliases.get(value, value)


def _normalize_product_fact(field: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.casefold()).strip()
    if field == "motor":
        normalized = re.sub(r"\s+motor$", "", normalized)
    elif field == "battery":
        normalized = re.sub(r"\s+battery$", "", normalized)
    elif field == "range":
        normalized = re.sub(r"\s+max\s+range$", "", normalized)
    return normalized


def extract_product_canon(document: DocumentType) -> list[dict[str, str]]:
    """Extract only rows from explicit product/specification tables."""

    products: dict[str, dict[str, str]] = {}
    for table in document.tables:
        if len(table.rows) < 2:
            continue
        headers = [_clean(cell.text) for cell in table.rows[0].cells]
        normalized = [_normalize_header(header) for header in headers]
        header_set = set(normalized)
        if not {"model", "price", "battery", "motor"} <= header_set:
            continue
        for row in table.rows[1:]:
            values = [_clean(cell.text) for cell in row.cells]
            record = {
                key: value
                for key, value in zip(normalized, values, strict=False)
                if key and value
            }
            model = record.get("model", "")
            if not model:
                continue
            target = products.setdefault(model, {"model": model})
            for key, value in record.items():
                if key == "model":
                    continue
                existing = target.get(key)
                if existing is not None and existing != value:
                    if _normalize_product_fact(
                        key, existing
                    ) == _normalize_product_fact(key, value):
                        target[key] = max((existing, value), key=len)
                        continue
                    raise ValueError(
                        f"conflicting confirmed product fact for {model} {key}"
                    )
                target[key] = value
    if not products:
        raise ValueError("no confirmed product canon table was found")
    return [products[model] for model in sorted(products, key=str.casefold)]


def extract_risk_rules(document: DocumentType) -> list[dict[str, str]]:
    """Extract explicit avoid/boundary language without synthesizing new policy."""

    rules: list[dict[str, str]] = []
    for table in document.tables:
        if len(table.rows) < 2:
            continue
        headers = [_clean(cell.text) for cell in table.rows[0].cells]
        normalized = [_normalize_header(header) for header in headers]
        positions = {header: index for index, header in enumerate(normalized)}
        for row_number, row in enumerate(table.rows[1:], start=1):
            values = [_clean(cell.text) for cell in row.cells]
            if {"situation", "do_say", "avoid_saying"} <= positions.keys():
                rules.append(
                    {
                        "id": f"safe-language-{len(rules) + 1:03d}",
                        "type": "safe_language",
                        "situation": values[positions["situation"]],
                        "guidance": values[positions["do_say"]],
                        "avoid": values[positions["avoid_saying"]],
                    }
                )
            elif {"avoid", "use_instead"} <= positions.keys():
                rules.append(
                    {
                        "id": f"safer-alternative-{len(rules) + 1:03d}",
                        "type": "safer_alternative",
                        "situation": "",
                        "guidance": values[positions["use_instead"]],
                        "avoid": values[positions["avoid"]],
                    }
                )
            elif "stage_id" in positions and (
                "risk_boundary" in positions or len(values) >= 5
            ):
                situation_index = positions.get("trigger", 2)
                guidance_index = positions.get("strategy", 3)
                boundary_index = positions.get("risk_boundary", 4)
                rules.append(
                    {
                        "id": values[positions["stage_id"]]
                        or f"stage-boundary-{row_number:03d}",
                        "type": "stage_boundary",
                        "situation": values[situation_index],
                        "guidance": values[guidance_index],
                        "avoid": values[boundary_index],
                    }
                )

    # Paragraph-level prohibitions are copied verbatim and remain source-grounded.
    for paragraph in document.paragraphs:
        text = _clean(paragraph.text)
        lower = text.casefold()
        if text and (
            lower.startswith("do not ")
            or lower.startswith("never ")
            or lower.startswith("avoid ")
        ):
            rules.append(
                {
                    "id": f"explicit-statement-{len(rules) + 1:03d}",
                    "type": "explicit_statement",
                    "situation": "",
                    "guidance": "",
                    "avoid": text,
                }
            )
    if not rules:
        raise ValueError("no explicit risk rules were found")
    return rules


def _json_text(payload: object) -> str:
    return json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"


def _render_package(
    group: str,
    chunks: list[Chunk],
    source_identifier: str,
    source_hash: str,
    version: str,
) -> str:
    title = {
        "kol": "KOL Cooperation",
        "pre-sales": "Pre-Sales",
        "order-logistics": "Order and Logistics",
        "after-sales": "After-Sales",
    }[group]
    route = DEPARTMENT_ROUTES[group]
    lines = [
        f"# {title}",
        "",
        f"Source: {source_identifier}",
        f"Source SHA256: {source_hash}",
        f"Version: {version}",
        f"Format version: {FORMAT_VERSION}",
        "",
        "## Route",
        "",
    ]
    if route["gmail_label"]:
        lines.append(f"Gmail label: {route['gmail_label']}")
    if route["department"]:
        lines.append(f"Department: {route['department']}")
    if not route["department"]:
        lines.append("Department: none")

    for chunk in chunks:
        lines.extend(
            [
                "",
                f"## {' > '.join(chunk.heading_path)}",
                "",
                f"Heading: {chunk.heading}",
                f"Heading level: {chunk.heading_level}",
                f"Content SHA256: {_text_sha256(chunk.content)}",
                "",
                chunk.content,
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _resolve_version(source: Path, version: str) -> str:
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise ValueError("version must use the form vMAJOR.MINOR")
    match = re.search(
        r"(?:^|_)v(\d+\.\d+)(?=_|\.|$)", source.name, re.IGNORECASE
    )
    if match and version.casefold() != f"v{match.group(1)}".casefold():
        raise ValueError("explicit version does not match source filename")
    return version


def _extract_source_versions(
    document: DocumentType, declared_version: str
) -> list[str]:
    versions = {declared_version.casefold()}
    for index, paragraph in enumerate(document.paragraphs):
        style = paragraph.style.name if paragraph.style is not None else ""
        if index >= 10 and not style.startswith("Heading"):
            continue
        versions.update(
            match.casefold()
            for match in re.findall(r"\bv\d+\.\d+\b", paragraph.text, re.IGNORECASE)
        )
    return sorted(
        versions,
        key=lambda value: tuple(int(part) for part in value[1:].split(".")),
    )


def _validate_staged_output(
    staging: Path, manifest: dict[str, object]
) -> None:
    expected = {
        *(f"{group}.md" for group in GROUPS),
        "routing_rules.json",
        "product_canon.json",
        "risk_rules.json",
        "manifest.json",
    }
    actual = {path.name for path in staging.iterdir() if path.is_file()}
    if actual != expected:
        raise ValueError("staging validation failed: incomplete artifact set")
    for filename, metadata in manifest["artifacts"].items():
        artifact = staging / filename
        if (
            _sha256(artifact) != metadata["sha256"]
            or artifact.stat().st_size != metadata["bytes"]
        ):
            raise ValueError(f"staging validation failed: {filename} hash mismatch")
    for group, metadata in manifest["packages"].items():
        if metadata["source_chunk_count"] <= 0:
            raise ValueError(f"staging validation failed: {group} has no source chunks")
    coverage = manifest["coverage"]
    if coverage["extracted_substantive_chunk_count"] != (
        coverage["routed_source_chunk_count"]
        + coverage["allowlisted_chunk_count"]
    ):
        raise ValueError("staging validation failed: chunk coverage mismatch")


def _stage_and_promote(
    output_path: Path,
    artifact_texts: dict[str, str],
    manifest: dict[str, object],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_texts = {**artifact_texts, "manifest.json": _json_text(manifest)}
    for stale in sorted(
        output_path.parent.glob(f".{output_path.name}-staging-*"),
        key=lambda path: path.name,
    ):
        if not stale.is_dir():
            raise ValueError(f"unsafe stale staging entry: {stale.name}")
        entries = {path.name for path in stale.iterdir()}
        if not entries <= set(all_texts) or any(path.is_dir() for path in stale.iterdir()):
            raise ValueError(f"unsafe stale staging contents: {stale.name}")
        for filename in all_texts:
            stale_file = stale / filename
            if stale_file.is_file():
                stale_file.unlink()
        stale.rmdir()

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_path.name}-staging-", dir=output_path.parent
        )
    )
    try:
        for filename, text in all_texts.items():
            (staging / filename).write_text(text, encoding="utf-8", newline="\n")
        _validate_staged_output(staging, manifest)

        if not output_path.exists():
            try:
                os.replace(staging, output_path)
            except PermissionError:
                output_path.mkdir()
                try:
                    for filename in sorted(all_texts):
                        os.replace(staging / filename, output_path / filename)
                except Exception:
                    for filename in all_texts:
                        promoted_file = output_path / filename
                        if promoted_file.is_file():
                            promoted_file.unlink()
                    output_path.rmdir()
                    raise
            return

        existing_files = {
            path.name for path in output_path.iterdir() if path.is_file()
        }
        if not existing_files:
            output_path.rmdir()
            os.replace(staging, output_path)
            return
        if existing_files != set(all_texts):
            raise ValueError("existing output is not a complete artifact set")

        previous = {
            filename: (output_path / filename).read_bytes()
            for filename in all_texts
        }
        try:
            for filename in sorted(all_texts):
                os.replace(staging / filename, output_path / filename)
        except Exception:
            for filename, content in previous.items():
                (output_path / filename).write_bytes(content)
            raise
    finally:
        if staging.exists():
            for filename in all_texts:
                staged_file = staging / filename
                if staged_file.is_file():
                    staged_file.unlink()
            staging.rmdir()


def build_knowledge(
    source: str | Path,
    output: str | Path,
    *,
    version: str,
) -> dict[str, object]:
    source_path = Path(source).resolve()
    output_path = Path(output)
    resolved_version = _resolve_version(source_path, version)
    source_identifier = source_path.name
    before_hash = _sha256(source_path)
    document = Document(source_path)
    chunks = extract_chunks(document)
    source_versions = _extract_source_versions(document, resolved_version)
    routed: dict[str, list[Chunk]] = {group: [] for group in GROUPS}
    allowlisted: list[Chunk] = []
    unmapped: list[Chunk] = []
    for chunk in chunks:
        group = route_chunk(chunk)
        if group is not None:
            routed[group].append(chunk)
        elif _is_allowlisted(chunk):
            allowlisted.append(chunk)
        else:
            unmapped.append(chunk)
    if unmapped:
        headings = "; ".join(chunk.heading for chunk in unmapped)
        raise ValueError(f"substantive knowledge chunks are not routed: {headings}")
    product_canon = extract_product_canon(document)
    risk_rules = extract_risk_rules(document)
    after_hash = _sha256(source_path)
    if after_hash != before_hash:
        raise RuntimeError("source DOCX changed during knowledge extraction")

    package_texts = {
        group: _render_package(
            group,
            routed[group],
            source_identifier,
            before_hash,
            resolved_version,
        )
        for group in GROUPS
    }
    source_metadata = {"identifier": source_identifier, "sha256": before_hash}
    routing_payload = {
        "format_version": FORMAT_VERSION,
        "version": resolved_version,
        "source_versions": source_versions,
        "source": source_metadata,
        "precedence": [
            "declarative leaf ID",
            "narrow leaf-heading fallback",
            "declarative section",
            "declarative root prefix",
        ],
        "section_routes": SECTION_ROUTES,
        "leaf_id_routes": LEAF_ID_ROUTES,
        "root_prefix_routes": ROOT_PREFIX_ROUTES,
        "allowlisted_headings": sorted(ALLOWLISTED_HEADINGS),
        "groups": DEPARTMENT_ROUTES,
    }
    canon_payload = {
        "format_version": FORMAT_VERSION,
        "version": resolved_version,
        "source_versions": source_versions,
        "source": source_metadata,
        "products": product_canon,
    }
    risks_payload = {
        "format_version": FORMAT_VERSION,
        "version": resolved_version,
        "source_versions": source_versions,
        "source": source_metadata,
        "rules": risk_rules,
    }
    artifact_texts: dict[str, str] = {
        **{f"{group}.md": text for group, text in package_texts.items()},
        "routing_rules.json": _json_text(routing_payload),
        "product_canon.json": _json_text(canon_payload),
        "risk_rules.json": _json_text(risks_payload),
    }
    artifacts = {
        filename: {
            "bytes": len(text.encode("utf-8")),
            "sha256": _text_sha256(text),
        }
        for filename, text in sorted(artifact_texts.items())
    }
    manifest: dict[str, object] = {
        "format_version": FORMAT_VERSION,
        "version": resolved_version,
        "source_versions": source_versions,
        "source": {
            "identifier": source_identifier,
            "sha256": before_hash,
            "sha256_before": before_hash,
            "sha256_after": after_hash,
        },
        "packages": {
            group: {
                "filename": f"{group}.md",
                "source_chunk_count": len(routed[group]),
                "total_chunk_count": len(routed[group]) + 1,
                "sha256": artifacts[f"{group}.md"]["sha256"],
            }
            for group in GROUPS
        },
        "coverage": {
            "extracted_substantive_chunk_count": len(chunks),
            "routed_source_chunk_count": sum(len(items) for items in routed.values()),
            "allowlisted_chunk_count": len(allowlisted),
            "allowlisted_headings": [chunk.heading for chunk in allowlisted],
        },
        "artifacts": artifacts,
    }
    _stage_and_promote(output_path, artifact_texts, manifest)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(r"E:\himiway"))
    parser.add_argument("--filename", default=SOURCE_FILENAME)
    parser.add_argument("--output", type=Path, default=Path("knowledge"))
    parser.add_argument("--version", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = locate_source(args.source_root, args.filename)
    manifest = build_knowledge(source, args.output, version=args.version)
    print(
        _json_text(
            {
                "source": manifest["source"],
                "packages": manifest["packages"],
            }
        ).rstrip()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
