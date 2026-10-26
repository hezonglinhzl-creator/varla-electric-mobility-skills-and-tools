"""Deterministic, source-grounded reply previews with exact proof handling."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any, Literal, Mapping, Protocol, Sequence, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from app.catalog import (
    APPROVED_CATALOG_HASHES,
    CatalogTemplate,
    LocalCatalog,
    load_local_catalog,
    locate_reply_assistant_seed,
    product_hits,
    render_template,
    select_template,
)
from app.grounding import (
    build_variants,
    canonical_warnings,
    canonicalize_sources,
    neutralize_header_lines,
    validate_index_hit,
)
from app.knowledge import (
    KnowledgeHit,
    KnowledgeIndex,
    KnowledgeVerificationContext,
    VALID_GROUPS,
)
from app.risk_policy import (
    APPROVED_TEMPLATE_REGISTRY,
    TemplateProof,
    approved_template_proof,
    content_risk_reasons,
)


class SearchIndex(Protocol):
    def search(
        self, query: str, *, group: str, limit: int = 5
    ) -> list[KnowledgeHit]: ...



@runtime_checkable
class ManifestBackedSearchIndex(SearchIndex, Protocol):
    """Search provider carrying an issued active-manifest verifier capability."""

    @property
    def verification_context(self) -> KnowledgeVerificationContext | None: ...


class ReplyPreview(BaseModel):
    """A reviewable reply whose sources and policy proof remain visible."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    status: Literal["previewed", "needs_knowledge", "manual_review"]
    group: str
    body: str | None
    variants: dict[str, list[str]] = Field(default_factory=dict)
    sources: list[KnowledgeHit] = Field(default_factory=list)
    knowledge_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    scenario_id: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    template_hash: str | None = None
    proof: TemplateProof | None = None

    def proof_for_body(self, body: str | None) -> TemplateProof | None:
        if (
            body is None
            or self.proof is None
            or self.scenario_id is None
            or self.template_id is None
            or self.template_version is None
        ):
            return None
        return approved_template_proof(
            text=body,
            group=self.group,
            action="reply",
            scenario_id=self.scenario_id,
            template_id=self.template_id,
            template_version=self.template_version,
        )


def _context_value(context: object, key: str) -> Any:
    if isinstance(context, Mapping):
        return context.get(key)
    return getattr(context, key, None)


def _policy_template(
    stage_id: str | None,
    group: str,
) -> tuple[str, str, str, str] | None:
    if not stage_id:
        return None
    for (scenario_id, template_id, version), approved in sorted(
        APPROVED_TEMPLATE_REGISTRY.items()
    ):
        if (
            stage_id in {scenario_id, template_id}
            and (group, "reply") in approved.allowed_group_actions
        ):
            return scenario_id, template_id, version, approved.body
    return None


def _selected_body(
    variants: Mapping[str, list[str]],
    tone: str | None,
    platform: str | None,
) -> str:
    requested = (tone or platform or "natural").casefold()
    if requested in {"gmail", "email", "formal"}:
        return variants["Formal"][0]
    if requested in {"instagram", "ig", "tiktok", "dm", "short"}:
        return variants["Short"][0]
    return variants["Natural"][0]


_CREATOR_REVIEW_STAGES = frozenset(
    {
        "ask_partnership_details",
        "ask_missing_creator_links",
        "ask_missing_creator_metrics",
    }
)
_COLLABORATION_MODEL_RE = re.compile(
    r"(?<![a-z0-9])(?:varla\s+)?(m5s|m7s)(?![a-z0-9])",
    re.I,
)


def _acknowledge_requested_collaboration_model(
    body: str,
    message: str,
    *,
    group: str,
    stage_id: str | None,
) -> str:
    """Make creator-review drafts answer the product named in the latest mail."""
    if group != "kol" or stage_id not in _CREATOR_REVIEW_STAGES:
        return body
    match = _COLLABORATION_MODEL_RE.search(message)
    if match is None:
        return body
    model = match.group(1).upper()
    if re.search(rf"(?<![a-z0-9]){re.escape(model)}(?![a-z0-9])", body, re.I):
        return body
    acknowledgement = (
        f"Thank you for sharing your interest in creating content for the {model}."
    )
    paragraphs = body.split("\n\n")
    if len(paragraphs) > 1:
        paragraphs.insert(1, acknowledgement)
        return "\n\n".join(paragraphs)
    return f"{acknowledgement}\n\n{body}"


def _knowledge_version(sources: Sequence[KnowledgeHit]) -> str | None:
    versions = sorted(
        {source.version for source in sources if source.version},
        key=str.casefold,
    )
    return " | ".join(versions) if versions else None


def _manual_warning(reasons: Sequence[str]) -> str:
    return "Manual review required: " + ", ".join(
        sorted(set(reasons), key=str.casefold)
    )


def _catalog_template_source(
    template: CatalogTemplate,
    rendered: str,
    group: str,
) -> KnowledgeHit:
    return KnowledgeHit(
        group=group,
        title=template.id,
        content=rendered,
        source=template.source,
        version=template.version,
        content_hash=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        score=-1.0,
    )


def _policy_template_source(
    *,
    scenario_id: str,
    template_id: str,
    version: str,
    body: str,
    group: str,
) -> KnowledgeHit:
    return KnowledgeHit(
        group=group,
        title=scenario_id,
        content=body,
        source="risk_policy.py",
        version=version,
        content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
        score=-1.0,
    )


class ReplyEngine:
    """Generate previews from manifest-backed index rows and approved catalogs."""

    def __init__(
        self,
        index: KnowledgeIndex | SearchIndex,
        *,
        catalog: LocalCatalog | None = None,
        catalog_seed_directory: str | Path | None = None,
        catalog_search_root: str | Path = Path("E:/himiway"),
        approved_catalog_hashes: Mapping[str, object] | None = None,
    ) -> None:
        self._index = index
        candidate_context = (
            index.verification_context
            if isinstance(index, ManifestBackedSearchIndex)
            else None
        )
        self._knowledge_verifier = (
            candidate_context
            if isinstance(candidate_context, KnowledgeVerificationContext)
            else None
        )
        if catalog is not None:
            if not isinstance(catalog, LocalCatalog):
                raise TypeError("catalog must be a LocalCatalog")
            self._catalog = catalog
            return
        if catalog_seed_directory is None and approved_catalog_hashes is None:
            self._catalog = LocalCatalog.empty()
            return
        try:
            self._catalog = load_local_catalog(
                seed_directory=catalog_seed_directory,
                search_root=catalog_search_root,
                approved_hashes=approved_catalog_hashes,
            )
        except (FileNotFoundError, ValueError, OSError):
            self._catalog = LocalCatalog.empty(
                warnings=(
                    "Catalog load failed; approved templates and product "
                    "specifications are unavailable.",
                ),
                requires_manual_review=True,
            )

    def generate(
        self,
        message: str,
        group: str,
        classification: object | None = None,
        *,
        source_risk_flags: Sequence[str] | None = None,
        tone: str | None = None,
        thread_context: object | None = None,
        variables: Mapping[str, object] | None = None,
        limit: int = 5,
    ) -> ReplyPreview:
        if group not in VALID_GROUPS:
            raise ValueError(f"invalid confirmed knowledge group: {group!r}")

        supplied_flags: set[str] = set()
        if isinstance(classification, (list, tuple, set, frozenset)):
            supplied_flags.update(
                flag for flag in classification if isinstance(flag, str) and flag
            )
            classification = None
        if isinstance(source_risk_flags, (list, tuple, set, frozenset)):
            supplied_flags.update(
                flag for flag in source_risk_flags if isinstance(flag, str) and flag
            )
        classification_flags = _context_value(classification, "risk_flags")
        if isinstance(classification_flags, (list, tuple, set, frozenset)):
            supplied_flags.update(
                flag
                for flag in classification_flags
                if isinstance(flag, str) and flag
            )

        primary_group = _context_value(classification, "primary_group")
        secondary_group = _context_value(classification, "secondary_group")
        manual_reasons: set[str] = set(supplied_flags)
        if isinstance(primary_group, str) and primary_group != group:
            manual_reasons.add("classification group conflict")
        if isinstance(secondary_group, str) and secondary_group:
            manual_reasons.add("mixed classification")
        if isinstance(message, str):
            manual_reasons.update(content_risk_reasons(message))
        if self._catalog.requires_manual_review:
            manual_reasons.add("catalog verification required")

        warnings: list[str] = list(self._catalog.warnings)
        stage_id = _context_value(classification, "stage_id")
        if not isinstance(stage_id, str):
            stage_id = None
        platform = _context_value(classification, "platform")
        if not isinstance(platform, str):
            platform = tone if tone in {"gmail", "instagram", "tiktok"} else None

        if not isinstance(message, str) or not message.strip():
            warnings.append("A non-empty message is required for knowledge retrieval.")
            if manual_reasons:
                warnings.append(_manual_warning(tuple(manual_reasons)))
            return ReplyPreview(
                status="manual_review" if manual_reasons else "needs_knowledge",
                group=group,
                body=None,
                warnings=canonical_warnings(warnings),
            )
        normalized_message = message.strip()

        scenario_id: str | None = None
        template_id: str | None = None
        template_version: str | None = None
        policy_body: str | None = None
        trusted_sources: list[KnowledgeHit] = []

        policy_template = _policy_template(stage_id, group)
        if policy_template is not None:
            scenario_id, template_id, template_version, policy_body = policy_template
            trusted_sources.append(
                _policy_template_source(
                    scenario_id=scenario_id,
                    template_id=template_id,
                    version=template_version,
                    body=policy_body,
                    group=group,
                )
            )

        selected_template = (
            None
            if policy_template is not None
            else select_template(
                self._catalog,
                stage_id=stage_id,
                platform=platform,
                group=group,
            )
        )
        rendered_template: str | None = None
        if selected_template is not None:
            merged_variables: dict[str, object] = {}
            if isinstance(thread_context, Mapping):
                merged_variables.update(thread_context)
            if variables:
                merged_variables.update(variables)
            rendered_template, render_warnings = render_template(
                selected_template, merged_variables
            )
            warnings.extend(render_warnings)
            if rendered_template is not None:
                template_id = selected_template.id
                template_version = selected_template.version
                warnings.extend(selected_template.risk_notes)
                trusted_sources.append(
                    _catalog_template_source(selected_template, rendered_template, group)
                )

        trusted_sources.extend(
            product_hits(normalized_message, group, self._catalog)
        )

        raw_hits: list[object] = []
        try:
            searched = self._index.search(
                normalized_message,
                group=group,
                limit=limit,
            )
            if isinstance(searched, list):
                raw_hits = list(searched)
            else:
                warnings.append("Malformed knowledge index result was discarded.")
        except Exception:
            warnings.append("Knowledge index search failed.")
            manual_reasons.add("knowledge index unavailable")
        verified_hits = [
            validated
            for raw_hit in raw_hits
            if (
                validated := validate_index_hit(
                    raw_hit,
                    confirmed_group=group,
                    index=self._knowledge_verifier,
                )
            )
            is not None
        ]
        if len(verified_hits) != len(raw_hits):
            warnings.append(
                "Unverified, cross-group, or malformed knowledge hits were discarded."
            )
        trusted_sources.extend(verified_hits)
        sources = canonicalize_sources(trusted_sources)

        if not sources:
            warnings.append(
                "No approved catalog fact or verified knowledge hit exists "
                "in the confirmed group."
            )
            if manual_reasons:
                warnings.append(_manual_warning(tuple(manual_reasons)))
            return ReplyPreview(
                status="manual_review" if manual_reasons else "needs_knowledge",
                group=group,
                body=None,
                warnings=canonical_warnings(warnings),
            )

        if policy_body is not None:
            payload = policy_body
        elif rendered_template is not None:
            payload = rendered_template
        else:
            payload = "\n\n".join(source.content for source in sources)

        try:
            variants = build_variants(payload, sources)
        except ValueError:
            warnings.append("Unsafe reply or citation content was rejected.")
            manual_reasons.add("unsafe reply content")
            warnings.append(_manual_warning(tuple(manual_reasons)))
            return ReplyPreview(
                status="manual_review",
                group=group,
                body=None,
                sources=sources,
                knowledge_version=_knowledge_version(sources),
                warnings=canonical_warnings(warnings),
            )
        body = (
            neutralize_header_lines(policy_body)
            if policy_body is not None
            else _selected_body(variants, tone, platform)
        )
        if policy_body is None:
            body = _acknowledge_requested_collaboration_model(
                body,
                normalized_message,
                group=group,
                stage_id=stage_id,
            )
        manual_reasons.update(content_risk_reasons(body))

        proof: TemplateProof | None = None
        if (
            policy_body is not None
            and scenario_id
            and template_id
            and template_version
            and not manual_reasons
        ):
            proof = approved_template_proof(
                text=body,
                group=group,
                action="reply",
                scenario_id=scenario_id,
                template_id=template_id,
                template_version=template_version,
            )

        status: Literal["previewed", "manual_review"] = (
            "manual_review" if manual_reasons else "previewed"
        )
        if manual_reasons:
            warnings.append(_manual_warning(tuple(manual_reasons)))

        return ReplyPreview(
            status=status,
            group=group,
            body=body,
            variants=variants,
            sources=sources,
            knowledge_version=_knowledge_version(sources),
            warnings=canonical_warnings(warnings),
            scenario_id=scenario_id,
            template_id=template_id,
            template_version=template_version,
            template_hash=(
                hashlib.sha256(body.encode("utf-8")).hexdigest()
                if template_id is not None
                else None
            ),
            proof=proof,
        )


__all__ = [
    "APPROVED_CATALOG_HASHES",
    "LocalCatalog",
    "ManifestBackedSearchIndex",
    "ReplyEngine",
    "ReplyPreview",
    "load_local_catalog",
    "locate_reply_assistant_seed",
]
