"""Group-isolated, local SQLite full-text knowledge retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable


VALID_GROUPS = frozenset({"kol", "pre-sales", "order-logistics", "after-sales"})
EXPECTED_ARTIFACTS = frozenset(
    {
        *(f"{group}.md" for group in VALID_GROUPS),
        "routing_rules.json",
        "product_canon.json",
        "risk_rules.json",
    }
)
_ASCII_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RUN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_CJK_QUERY_ALIASES = {
    "合作": ("collaboration",),
    "产品交换": ("product", "exchange"),
    "刹车": ("brake",),
}
SCHEMA_VERSION = "2"
_CURRENT_FTS_COLUMNS = (
    "group_name",
    "title",
    "content",
    "search_terms",
    "source",
    "version",
    "content_hash",
)
_LEGACY_FTS_COLUMNS = (
    "group_name",
    "title",
    "content",
    "source",
    "version",
    "content_hash",
)


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    """A single knowledge result and its provenance."""

    group: str
    title: str
    content: str
    source: str
    version: str
    content_hash: str
    score: float


_VERIFICATION_CONTEXT_ISSUER = object()


class KnowledgeVerificationContext:
    """Issued capability bound to one validated active package generation."""

    __slots__ = ("_index", "active_manifest_hash")

    def __init__(
        self,
        index: "KnowledgeIndex",
        active_manifest_hash: str,
        issuer: object,
    ) -> None:
        if issuer is not _VERIFICATION_CONTEXT_ISSUER:
            raise ValueError("verification contexts are issued by KnowledgeIndex")
        self._index = index
        self.active_manifest_hash = active_manifest_hash

    def verify_hit(self, hit: object) -> bool:
        return (
            self._index.active_manifest_hash == self.active_manifest_hash
            and self._index.verify_hit(hit)
        )


class KnowledgeIndex:
    """FTS5 index that requires an explicit knowledge group for every search."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row

    @classmethod
    def in_memory(cls) -> "KnowledgeIndex":
        index = cls(sqlite3.connect(":memory:"))
        index.initialize()
        return index

    def _create_fts_table(self) -> None:
        self._connection.execute(
            """
            CREATE VIRTUAL TABLE knowledge_fts USING fts5(
                group_name UNINDEXED,
                title,
                content,
                search_terms,
                source UNINDEXED,
                version UNINDEXED,
                content_hash UNINDEXED,
                tokenize = 'unicode61'
            )
            """
        )

    def initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_verified_rows (
                row_fingerprint TEXT PRIMARY KEY,
                manifest_hash TEXT NOT NULL
            )
            """
        )
        self._connection.commit()
        exists = self._connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("knowledge_fts",),
        ).fetchone()
        if exists is None:
            self._create_fts_table()
        else:
            columns = tuple(
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(knowledge_fts)"
                ).fetchall()
            )
            if columns == _LEGACY_FTS_COLUMNS:
                legacy_rows = self._connection.execute(
                    """
                    SELECT group_name, title, content, source, version, content_hash
                    FROM knowledge_fts
                    ORDER BY rowid
                    """
                ).fetchall()
                try:
                    self._connection.execute("BEGIN IMMEDIATE")
                    self._connection.execute("DROP TABLE knowledge_fts")
                    self._create_fts_table()
                    self._connection.executemany(
                        """
                        INSERT INTO knowledge_fts
                            (group_name, title, content, search_terms,
                             source, version, content_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                row["group_name"],
                                row["title"],
                                row["content"],
                                self._cjk_search_terms(
                                    f"{row['title']} {row['content']}"
                                ),
                                row["source"],
                                row["version"],
                                row["content_hash"],
                            )
                            for row in legacy_rows
                        ],
                    )
                    self._connection.commit()
                except Exception:
                    self._connection.rollback()
                    raise
            elif columns != _CURRENT_FTS_COLUMNS:
                raise ValueError("unsupported knowledge index schema")
        self._connection.execute(
            """
            INSERT INTO knowledge_meta(key, value) VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (SCHEMA_VERSION,),
        )
        self._connection.commit()

    @staticmethod
    def _require_group(group: str) -> None:
        if group not in VALID_GROUPS:
            choices = ", ".join(sorted(VALID_GROUPS))
            raise ValueError(f"invalid knowledge group {group!r}; expected one of {choices}")

    def add(
        self,
        group: str,
        title: str,
        content: str,
        source: str = "",
        version: str = "",
        content_hash: str | None = None,
    ) -> None:
        self._require_group(group)
        normalized_content = content.strip()
        if not title.strip() or not normalized_content:
            raise ValueError("title and content must be non-empty")
        digest = content_hash or hashlib.sha256(
            normalized_content.encode("utf-8")
        ).hexdigest()
        search_terms = self._cjk_search_terms(f"{title} {normalized_content}")
        self._connection.execute(
            """
            INSERT INTO knowledge_fts
                (group_name, title, content, search_terms, source, version, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group,
                title.strip(),
                normalized_content,
                search_terms,
                str(source),
                str(version),
                digest,
            ),
        )
        self._connection.commit()

    @staticmethod
    def _cjk_search_terms(text: str) -> str:
        tokens: list[str] = []
        for run in _CJK_RUN_RE.findall(text):
            tokens.extend(run)
            tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
        return " ".join(tokens)

    @staticmethod
    def _safe_match_query(query: str) -> str | None:
        tokens = _ASCII_WORD_RE.findall(query)
        for run in _CJK_RUN_RE.findall(query):
            if len(run) == 1:
                tokens.append(run)
            else:
                tokens.extend(
                    run[index : index + 2] for index in range(len(run) - 1)
                )
        if not tokens:
            return None
        # Quoting tokens makes FTS operators, punctuation, and unmatched quotes inert.
        quoted = [
            f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens
        ]
        base = " AND ".join(quoted)
        aliases = _CJK_QUERY_ALIASES.get(query.strip())
        if aliases:
            alias_query = " AND ".join(f'"{token}"' for token in aliases)
            return f"({base}) OR ({alias_query})"
        return base

    def search(
        self, query: str, *, group: str, limit: int = 5
    ) -> list[KnowledgeHit]:
        self._require_group(group)
        if limit <= 0:
            return []
        match_query = self._safe_match_query(query.strip())
        if match_query is None:
            return []
        rows = self._connection.execute(
            """
            SELECT
                group_name,
                title,
                content,
                source,
                version,
                content_hash,
                bm25(knowledge_fts, 0.0, 3.0, 1.0, 0.8, 0.0, 0.0, 0.0) AS score
            FROM knowledge_fts
            WHERE knowledge_fts MATCH ?
              AND group_name = ?
            ORDER BY score ASC, title COLLATE NOCASE ASC,
                     source COLLATE NOCASE ASC, content_hash ASC, rowid ASC
            LIMIT ?
            """,
            (match_query, group, min(int(limit), 100)),
        ).fetchall()
        return [
            KnowledgeHit(
                group=row["group_name"],
                title=row["title"],
                content=row["content"],
                source=row["source"],
                version=row["version"],
                content_hash=row["content_hash"],
                score=float(row["score"]),
            )
            for row in rows
        ]

    @staticmethod
    def _row_fingerprint(row: tuple[str, ...]) -> str:
        encoded = json.dumps(
            list(row),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def verify_hit(self, hit: object) -> bool:
        """Verify a hit against a row promoted from the active package manifest."""

        if not isinstance(hit, KnowledgeHit):
            return False
        values = (
            hit.group,
            hit.title,
            hit.content,
            hit.source,
            hit.version,
            hit.content_hash,
        )
        if not all(isinstance(value, str) for value in values):
            return False
        normalized_content = hit.content.strip()
        if (
            not normalized_content
            or normalized_content != hit.content
            or hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
            != hit.content_hash.casefold()
        ):
            return False
        manifest_row = self._connection.execute(
            "SELECT value FROM knowledge_meta WHERE key = 'active_manifest_hash'"
        ).fetchone()
        if manifest_row is None:
            return False
        fingerprint = self._row_fingerprint(
            (
                hit.group,
                hit.title,
                hit.content,
                hit.source,
                hit.version,
                hit.content_hash.casefold(),
            )
        )
        verified = self._connection.execute(
            """
            SELECT 1
            FROM knowledge_verified_rows
            WHERE row_fingerprint = ? AND manifest_hash = ?
            """,
            (fingerprint, manifest_row["value"]),
        ).fetchone()
        if verified is None:
            return False
        stored = self._connection.execute(
            """
            SELECT 1
            FROM knowledge_fts
            WHERE group_name = ?
              AND title = ?
              AND content = ?
              AND source = ?
              AND version = ?
              AND content_hash = ?
            LIMIT 1
            """,
            (
                hit.group,
                hit.title,
                hit.content,
                hit.source,
                hit.version,
                hit.content_hash.casefold(),
            ),
        ).fetchone()
        return stored is not None

    @property
    def active_manifest_hash(self) -> str | None:
        row = self._connection.execute(
            "SELECT value FROM knowledge_meta WHERE key = 'active_manifest_hash'"
        ).fetchone()
        if row is None:
            return None
        value = row["value"]
        return value if isinstance(value, str) and len(value) == 64 else None

    @property
    def verification_context(self) -> KnowledgeVerificationContext | None:
        active_hash = self.active_manifest_hash
        if active_hash is None:
            return None
        return KnowledgeVerificationContext(
            self,
            active_hash,
            _VERIFICATION_CONTEXT_ISSUER,
        )

    @staticmethod
    def _parse_markdown(path: Path, group: str) -> list[tuple[str, ...]]:
        text = path.read_text(encoding="utf-8")
        source_match = re.search(r"^Source:\s+(.+)$", text, re.MULTILINE)
        version_match = re.search(r"^Version:\s+(.+)$", text, re.MULTILINE)
        source = source_match.group(1).strip() if source_match else str(path)
        version = version_match.group(1).strip() if version_match else ""
        sections = list(_SECTION_RE.finditer(text))
        rows: list[tuple[str, ...]] = []
        for index, match in enumerate(sections):
            start = match.end()
            end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
            content = text[start:end].strip()
            if not content:
                continue
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            title = match.group(1).strip()
            rows.append(
                (
                    group,
                    title,
                    content,
                    KnowledgeIndex._cjk_search_terms(f"{title} {content}"),
                    source,
                    version,
                    digest,
                )
            )
        return rows

    def _validate_staging(self, rows: Iterable[tuple[str, ...]]) -> bool:
        materialized = list(rows)
        return bool(materialized) and all(
            row[0] in VALID_GROUPS
            and bool(row[1].strip())
            and bool(row[2].strip())
            and len(row[6]) == 64
            for row in materialized
        )

    @staticmethod
    def _file_sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def _validate_manifest(cls, root: Path) -> dict[str, object]:
        markdown_names = {path.name for path in root.glob("*.md") if path.is_file()}
        expected_markdown = {f"{group}.md" for group in VALID_GROUPS}
        if markdown_names != expected_markdown:
            raise ValueError("complete set of four exact knowledge package files required")
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError("knowledge manifest is required")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise ValueError("knowledge manifest is invalid") from error

        version = manifest.get("version")
        source_versions = manifest.get("source_versions")
        source = manifest.get("source")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("manifest version is required")
        if (
            not isinstance(source_versions, list)
            or version not in source_versions
            or not all(isinstance(item, str) for item in source_versions)
        ):
            raise ValueError("manifest source versions are invalid")
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("identifier"), str)
            or not source["identifier"].strip()
            or not isinstance(source.get("sha256"), str)
            or len(source["sha256"]) != 64
        ):
            raise ValueError("manifest source identifier and hash are required")

        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != EXPECTED_ARTIFACTS:
            raise ValueError("manifest must declare the complete artifact set")
        for filename, metadata in artifacts.items():
            artifact = root / filename
            if not artifact.is_file() or not isinstance(metadata, dict):
                raise ValueError(f"manifest artifact missing: {filename}")
            if metadata.get("sha256") != cls._file_sha256(artifact):
                raise ValueError(f"manifest artifact hash mismatch: {filename}")
            if metadata.get("bytes") != artifact.stat().st_size:
                raise ValueError(f"manifest artifact size mismatch: {filename}")

        packages = manifest.get("packages")
        if not isinstance(packages, dict) or set(packages) != VALID_GROUPS:
            raise ValueError("manifest package metadata is incomplete")
        for group, metadata in packages.items():
            expected_filename = f"{group}.md"
            source_count = metadata.get("source_chunk_count")
            total_count = metadata.get("total_chunk_count")
            if (
                metadata.get("filename") != expected_filename
                or not isinstance(source_count, int)
                or source_count <= 0
                or total_count != source_count + 1
                or metadata.get("sha256")
                != artifacts[expected_filename].get("sha256")
            ):
                raise ValueError(f"invalid package metadata for {group}")

        for filename in ("routing_rules.json", "product_canon.json", "risk_rules.json"):
            payload = json.loads((root / filename).read_text(encoding="utf-8"))
            expected_source = {
                "identifier": source["identifier"],
                "sha256": source["sha256"],
            }
            if (
                payload.get("version") != version
                or payload.get("source_versions") != source_versions
                or payload.get("source") != expected_source
            ):
                raise ValueError(f"source/version mismatch in {filename}")
        coverage = manifest.get("coverage")
        if not isinstance(coverage, dict):
            raise ValueError("manifest coverage accounting is required")
        routed_count = sum(
            metadata["source_chunk_count"] for metadata in packages.values()
        )
        if (
            coverage.get("routed_source_chunk_count") != routed_count
            or coverage.get("extracted_substantive_chunk_count")
            != routed_count + coverage.get("allowlisted_chunk_count", -1)
        ):
            raise ValueError("manifest chunk coverage is invalid")
        return manifest

    def _after_staging_insert(self) -> None:
        """Internal transaction checkpoint used by fault-injection tests."""

    def rebuild_from_directory(self, directory: str | Path) -> int:
        """Validate all packages first, then replace the active index atomically."""

        root = Path(directory)
        manifest = self._validate_manifest(root)
        manifest_hash = self._file_sha256(root / "manifest.json")
        rows: list[tuple[str, ...]] = []
        for group in sorted(VALID_GROUPS):
            path = root / f"{group}.md"
            group_rows = self._parse_markdown(path, group)
            metadata = manifest["packages"][group]
            if len(group_rows) != metadata["total_chunk_count"]:
                raise ValueError(f"manifest chunk count mismatch for {group}")
            if any(
                row[4] != manifest["source"]["identifier"]
                or row[5] != manifest["version"]
                for row in group_rows
            ):
                raise ValueError(f"package source/version mismatch for {group}")
            rows.extend(group_rows)
        if not self._validate_staging(rows):
            raise ValueError("knowledge staging validation failed")

        try:
            self._connection.execute("BEGIN IMMEDIATE")
            self._connection.execute("DELETE FROM knowledge_fts")
            self._connection.executemany(
                """
                INSERT INTO knowledge_fts
                    (group_name, title, content, search_terms, source, version, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self._connection.execute("DELETE FROM knowledge_verified_rows")
            self._connection.executemany(
                """
                INSERT INTO knowledge_verified_rows(row_fingerprint, manifest_hash)
                VALUES (?, ?)
                """,
                [
                    (
                        self._row_fingerprint(
                            (
                                row[0],
                                row[1],
                                row[2],
                                row[4],
                                row[5],
                                row[6],
                            )
                        ),
                        manifest_hash,
                    )
                    for row in rows
                ],
            )
            self._connection.execute(
                """
                INSERT INTO knowledge_meta(key, value)
                VALUES ('active_manifest_hash', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (manifest_hash,),
            )
            self._after_staging_insert()
            inserted = self._connection.execute(
                "SELECT count(*) FROM knowledge_fts"
            ).fetchone()[0]
            if inserted != len(rows):
                raise ValueError("knowledge staging row-count validation failed")
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise
        return len(rows)
