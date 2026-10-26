"""Read-only, hash-approved reply template and product catalog."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from app.grounding import is_safe_component, is_safe_multiline_text, sanitize_variable
from app.knowledge import KnowledgeHit, VALID_GROUPS


APPROVED_CATALOG_HASHES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "templates.json": frozenset(
            {
                "4dbe259cb05dcfb984fd3bb8b912c77f5ac8109b745d90dc54e94927951ccbe9",
                "1bd22c5e8da87b40dee4666e6222ff15d318839f3b0ee0f39e5c9de5ea874eaf",
                "587eba030ca7e512a43876584913cfca22bd5773cc83561e66f62e7276f2b166",
                "f12108b8210de83a84901837cdb23272e8501e865e31fad5c2b47f8743972319",
                "cdf37f88455a361863cde289ad29676150bb4013de44b2e8b91386d37d8f4ab9",
                "b82dd47f7a9398cdf0ebd663c63b395a922cd89c483f72c17af4ce8c1d6de915",
                "3a432c3a74b7104bb5a85656cfebe6d20a6bba529da4ca7e60f5fe989fe20535",
            }
        ),
        "product_specs.json": frozenset(
            {"87c3c758caba4f01a9b36882b2ef31c06d2b7f92ee1618ea62bade00cbcf18e4"}
        ),
    }
)
_PLACEHOLDER_RE = re.compile(r"{{\s*([A-Za-z][A-Za-z0-9_]*)\s*}}")
_SPEC_QUERY_RE = re.compile(
    r"(?<![a-z0-9])(?:spec|specs|specification|specifications)(?![a-z0-9])",
    re.IGNORECASE,
)
_QUESTION_INTENT_RE = re.compile(
    r"(?<![a-z0-9])(?:what|which|how|does|do|is|are|tell me|give me)(?![a-z0-9])",
    re.IGNORECASE,
)
_FIELD_INTENT_PATTERNS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "price": (
            r"\b(?:price|cost|msrp)\b",
            r"\bstarts?\s+at\b",
            r"\bbuy\b",
        ),
        "motor": (
            r"\bmotor\b",
            r"\bwatts?\b",
            r"\bpeak\s+power\b",
        ),
        "battery": (r"\bbattery\b",),
        "controller": (r"\bcontroller\b",),
        "charger": (r"\b(?:charger|charging)\b",),
        "tires": (
            r"\b(?:tire|tires|tyre|tyres)\b",
            r"\bwheel\s+size\b",
        ),
        "front suspension": (r"\bfront\s+suspension\b", r"\bfork\b"),
        "rear suspension": (r"\brear\s+suspension\b", r"\brear\s+shock\b"),
        "brake": (r"\bbrakes?\b",),
        "light": (r"\b(?:light|lights|headlight|taillight)\b",),
        "max speed": (r"\b(?:max|maximum|top)\s+speed\b",),
        "range": (
            r"\brange\b",
            r"\bmiles?\s+per\s+charge\b",
            r"\bhow\s+far\b.*\b(?:go|travel|ride)\b",
        ),
        "waterproof rating": (r"\bwaterproof\b", r"\bip\s+rating\b"),
        "dimension": (
            r"\boverall\s+dimensions?\b",
            r"\bdimensions?\b",
            r"\bhow\s+(?:long|wide|tall)\b",
        ),
        "seat height": (r"\bseat\s+height\b",),
        "weight": (
            r"\b(?:vehicle|bike|product|net|gross)\s+weight\b",
            r"\bhow\s+much\b.*\bweighs?\b",
            r"\bweight\s+in\s+(?:lbs?|kg)\b",
        ),
        "loading capacity": (
            r"\b(?:loading|load|weight)\s+capacity\b",
            r"\bpayload\b",
            r"\b(?:maximum|max)\s+rider\s+weight\b",
            r"\bhow\s+much\s+weight\b.*\bcarry\b",
            r"\bcarry\b.*\bweight\b",
        ),
    }
)


@dataclass(frozen=True, slots=True)
class CatalogTemplate:
    id: str
    stage: str
    groups: tuple[str, ...]
    platforms: tuple[str, ...]
    tone: str
    body: str
    version: str
    source: str
    risk_notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    model: str
    facts: Mapping[str, str]
    version: str
    source: str


@dataclass(frozen=True, slots=True)
class LocalCatalog:
    templates: tuple[CatalogTemplate, ...]
    products: Mapping[str, CatalogProduct]
    source_hashes: Mapping[str, str]
    warnings: tuple[str, ...] = ()
    requires_manual_review: bool = False

    @classmethod
    def empty(
        cls,
        *,
        warnings: Iterable[str] = (),
        requires_manual_review: bool = False,
    ) -> "LocalCatalog":
        return cls(
            (),
            MappingProxyType({}),
            MappingProxyType({}),
            tuple(sorted(set(warnings), key=str.casefold)),
            requires_manual_review,
        )


def locate_reply_assistant_seed(search_root: str | Path = Path("E:/himiway")) -> Path:
    root = Path(search_root)
    if not root.is_dir():
        raise FileNotFoundError(f"reply-assistant search root is unavailable: {root}")
    matches = sorted(
        (
            candidate / "knowledge_seed"
            for candidate in root.rglob("varla-kol-reply-assistant")
            if candidate.is_dir()
            and candidate.name == "varla-kol-reply-assistant"
            and (candidate / "knowledge_seed" / "templates.json").is_file()
            and (candidate / "knowledge_seed" / "product_specs.json").is_file()
        ),
        key=lambda path: str(path).casefold(),
    )
    if not matches:
        raise FileNotFoundError(
            "exact varla-kol-reply-assistant knowledge_seed was not found"
        )
    if len(matches) != 1:
        raise ValueError("multiple exact varla-kol-reply-assistant catalogs found")
    return matches[0]


def _load_json_read_only(path: Path) -> tuple[Any, str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        return json.loads(raw.decode("utf-8-sig")), digest
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid catalog JSON: {path.name}") from error


def _approved_hash_values(
    approved_hashes: Mapping[str, object],
    filename: str,
) -> frozenset[str]:
    configured = approved_hashes.get(filename)
    if isinstance(configured, str):
        values = (configured,)
    elif isinstance(configured, (tuple, list, set, frozenset)):
        values = tuple(value for value in configured if isinstance(value, str))
    else:
        values = ()
    return frozenset(value.casefold() for value in values)


def _approval_mark(item: Mapping[str, Any]) -> bool | None:
    if "approved" not in item:
        return None
    approved = item["approved"]
    if approved is True or (
        isinstance(approved, str)
        and approved.strip().casefold() in {"approved", "true", "yes"}
    ):
        return True
    return False


def _template_groups(item: Mapping[str, Any], stage: str) -> tuple[str, ...]:
    declared = item.get("groups", item.get("group"))
    if isinstance(declared, str):
        candidates = (declared,)
    elif isinstance(declared, list):
        candidates = tuple(value for value in declared if isinstance(value, str))
    else:
        inferred: Mapping[str, str] = {
            "presales_service_question": "pre-sales",
            "product_specs_question": "pre-sales",
            "aftersales_service_question": "after-sales",
            "battery_life_question": "after-sales",
            "shipping_damage_claim": "after-sales",
            "return_label_question": "after-sales",
            "front_brake_line_routing_question": "after-sales",
            "shipping_timeline": "order-logistics",
        }
        candidates = (inferred.get(stage, "kol"),)
    return tuple(
        sorted(
            {
                value.strip()
                for value in candidates
                if value.strip() in VALID_GROUPS
            },
            key=str.casefold,
        )
    )


def load_local_catalog(
    *,
    seed_directory: str | Path | None = None,
    search_root: str | Path = Path("E:/himiway"),
    approved_hashes: Mapping[str, object] | None = None,
) -> LocalCatalog:
    seed = (
        Path(seed_directory)
        if seed_directory is not None
        else locate_reply_assistant_seed(search_root)
    )
    templates_path = seed / "templates.json"
    products_path = seed / "product_specs.json"
    if not templates_path.is_file() or not products_path.is_file():
        raise FileNotFoundError("templates.json and product_specs.json are required")

    template_payload, template_file_hash = _load_json_read_only(templates_path)
    product_payload, product_file_hash = _load_json_read_only(products_path)
    if not isinstance(template_payload, list) or not isinstance(product_payload, dict):
        raise ValueError("catalog JSON has an unsupported top-level shape")

    approval_registry = (
        APPROVED_CATALOG_HASHES if approved_hashes is None else approved_hashes
    )
    template_file_approved = (
        template_file_hash
        in _approved_hash_values(approval_registry, templates_path.name)
    )
    product_file_approved = (
        product_file_hash
        in _approved_hash_values(approval_registry, products_path.name)
    )
    warnings: list[str] = []
    if not template_file_approved:
        warnings.append(
            "Catalog hash is not approved for templates.json; "
            "unmarked templates are disabled."
        )
    if not product_file_approved:
        warnings.append(
            "Catalog hash is not approved for product_specs.json; "
            "product specifications are disabled."
        )

    template_version = f"sha256-{template_file_hash[:12]}"
    templates: list[CatalogTemplate] = []
    seen_ids: set[str] = set()
    rejected_unsafe_templates = 0
    for raw_item in template_payload:
        if not isinstance(raw_item, dict):
            continue
        approval_mark = _approval_mark(raw_item)
        status = raw_item.get("status")
        if approval_mark is False or (
            isinstance(status, str)
            and status.casefold() not in {"approved", "active"}
        ):
            continue
        if approval_mark is not True and not template_file_approved:
            continue
        template_id = raw_item.get("id")
        stage = raw_item.get("stage")
        body = raw_item.get("template")
        platforms = raw_item.get("platform")
        risk_notes = raw_item.get("riskNotes", [])
        if (
            not is_safe_component(template_id)
            or template_id in seen_ids
            or not is_safe_component(stage)
            or not is_safe_multiline_text(body)
            or not body.strip()
            or not isinstance(platforms, list)
            or not platforms
            or not all(is_safe_component(value) for value in platforms)
            or not isinstance(risk_notes, list)
            or not all(is_safe_multiline_text(value) for value in risk_notes)
        ):
            rejected_unsafe_templates += 1
            continue
        groups = _template_groups(raw_item, stage.strip())
        if not groups:
            continue
        seen_ids.add(template_id)
        templates.append(
            CatalogTemplate(
                id=template_id.strip(),
                stage=stage.strip(),
                groups=groups,
                platforms=tuple(
                    sorted(
                        {value.strip().casefold() for value in platforms},
                        key=str.casefold,
                    )
                ),
                tone=(
                    str(raw_item.get("tone", "")).strip().casefold()
                    if is_safe_component(str(raw_item.get("tone", "default")))
                    else ""
                ),
                body=body.strip(),
                version=(
                    str(raw_item["version"]).strip()
                    if is_safe_component(raw_item.get("version"))
                    else template_version
                ),
                source=templates_path.name,
                risk_notes=tuple(
                    sorted({note.strip() for note in risk_notes}, key=str.casefold)
                ),
            )
        )
    if rejected_unsafe_templates:
        warnings.append(
            f"Catalog rejected {rejected_unsafe_templates} unsafe template entries."
        )

    product_version = f"sha256-{product_file_hash[:12]}"
    products: dict[str, CatalogProduct] = {}
    rejected_product_facts = 0
    if product_file_approved:
        for raw_model, raw_facts in product_payload.items():
            if not is_safe_component(raw_model) or not isinstance(raw_facts, dict):
                rejected_product_facts += 1
                continue
            facts: dict[str, str] = {}
            for key, value in raw_facts.items():
                normalized_value = str(value).strip()
                if (
                    not is_safe_component(key)
                    or isinstance(value, bool)
                    or not isinstance(value, (str, int, float))
                    or not is_safe_component(normalized_value)
                ):
                    rejected_product_facts += 1
                    continue
                facts[key.strip()] = normalized_value
            if facts:
                model = raw_model.strip()
                products[model] = CatalogProduct(
                    model=model,
                    facts=MappingProxyType(facts),
                    version=product_version,
                    source=products_path.name,
                )
    if rejected_product_facts:
        warnings.append(
            f"Catalog rejected {rejected_product_facts} unsafe product facts."
        )

    return LocalCatalog(
        templates=tuple(sorted(templates, key=lambda item: item.id.casefold())),
        products=MappingProxyType(products),
        source_hashes=MappingProxyType(
            {
                templates_path.name: template_file_hash,
                products_path.name: product_file_hash,
            }
        ),
        warnings=tuple(sorted(set(warnings), key=str.casefold)),
        requires_manual_review=bool(warnings),
    )


def select_template(
    catalog: LocalCatalog,
    *,
    stage_id: str | None,
    platform: str | None,
    group: str,
) -> CatalogTemplate | None:
    if not stage_id:
        return None
    candidates = [
        template
        for template in catalog.templates
        if template.stage == stage_id and group in template.groups
    ]
    if not candidates:
        return None
    normalized_platform = platform.casefold() if platform else None
    if normalized_platform:
        scoped = [
            template
            for template in candidates
            if normalized_platform in template.platforms
        ]
        if scoped:
            candidates = scoped
    return sorted(candidates, key=lambda item: item.id.casefold())[0]


def render_template(
    template: CatalogTemplate,
    variables: Mapping[str, object],
) -> tuple[str | None, list[str]]:
    warnings: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = variables.get(name)
        if value is None and name.casefold() == "name":
            return "there"
        if value is None:
            warnings.append(f"Missing approved template variable: {name}")
            return match.group(0)
        return sanitize_variable(value)

    rendered = _PLACEHOLDER_RE.sub(replace, template.body)
    if _PLACEHOLDER_RE.search(rendered) or not is_safe_multiline_text(rendered):
        return None, warnings
    return rendered, warnings


def _phrase_present(text: str, phrase: str) -> bool:
    words = [re.escape(word) for word in phrase.casefold().split()]
    pattern = r"(?<![a-z0-9])" + r"\s+".join(words) + r"(?![a-z0-9])"
    return re.search(pattern, text.casefold()) is not None


def _field_intent_present(text: str, field: str) -> bool:
    patterns = _FIELD_INTENT_PATTERNS.get(field.casefold())
    if patterns is None:
        return _phrase_present(text, field)
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def product_hits(
    message: str,
    group: str,
    catalog: LocalCatalog,
) -> list[KnowledgeHit]:
    if group != "pre-sales":
        return []
    normalized = message.casefold()
    include_all = bool(_SPEC_QUERY_RE.search(normalized))
    question_intent = bool(_QUESTION_INTENT_RE.search(normalized))
    terse_spec_intent = len(re.findall(r"[a-z0-9]+", normalized)) <= 4
    hits: list[KnowledgeHit] = []
    for model, product in sorted(
        catalog.products.items(), key=lambda item: item[0].casefold()
    ):
        if not _phrase_present(normalized, model):
            continue
        ordered_facts = sorted(
            product.facts.items(), key=lambda item: item[0].casefold()
        )
        requested_fields = {
            field
            for field, _ in ordered_facts
            if _field_intent_present(normalized, field)
        }
        for field, value in ordered_facts:
            field_requested = field in requested_fields
            if not (
                (include_all and not requested_fields)
                or (field_requested and (question_intent or terse_spec_intent))
            ):
                continue
            content = f"{model} {field}: {value}"
            hits.append(
                KnowledgeHit(
                    group=group,
                    title=f"{model} {field}",
                    content=content,
                    source=product.source,
                    version=product.version,
                    content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    score=-1.0,
                )
            )
    return hits
