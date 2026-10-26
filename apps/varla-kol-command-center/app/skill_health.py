"""Independent, read-only health checks for the three KOL child skills."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Mapping
from uuid import uuid4

from docx import Document

from app.contract_gateway import ContractGateway
from app.gmail_gateway import EXPECTED_ACCOUNT, sanitize_error


COMMAND_TIMEOUT_SECONDS = 30
SKILL_NAMES = (
    "varla-gmail-automation",
    "varla-kol-contract-updater",
    "varla-kol-reply-assistant",
)
_AUTO = object()


def _replace_with_bounded_retry(source: Path, destination: Path) -> None:
    """Tolerate short Windows scanner/share locks without hiding real failures."""
    delays = (0.02, 0.05, 0.1)
    for delay in delays:
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            time.sleep(delay)
    os.replace(source, destination)


@dataclass(frozen=True, slots=True)
class GmailCredentials:
    credentials_path: Path
    token_path: Path
    expected_account: str

    @property
    def configured(self) -> bool:
        return (
            self.expected_account == EXPECTED_ACCOUNT
            and self.credentials_path.is_file()
            and self.token_path.is_file()
        )


@dataclass(frozen=True, slots=True)
class HealthStatus:
    name: str
    status: str
    enabled: bool
    version: str
    checks: Mapping[str, str]
    error: str | None = None
    drift: bool = False


Runner = Callable[..., Any]
Clock = Callable[[], datetime]
Checker = Callable[[], HealthStatus]


def _resolve_python() -> str | None:
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "python"
        / "python.exe"
    )
    if bundled.is_file():
        return str(bundled)
    return shutil.which("python")


def _resolve_node() -> str | None:
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin"
        / "node.exe"
    )
    if bundled.is_file():
        return str(bundled)
    return shutil.which("node")


def _default_reply_root() -> Path | None:
    configured = os.environ.get("VARLA_REPLY_ASSISTANT_ROOT")
    candidates = [
        Path(configured) if configured else None,
        Path(r"E:\himiway\KOL回复训练\脚本\varla-kol-reply-assistant"),
        Path(r"D:\项目\himiway\KOL回复训练\脚本\varla-kol-reply-assistant"),
    ]
    return next(
        (candidate for candidate in candidates if candidate and candidate.is_dir()),
        None,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*[\"']?([^\"'\r\n]+)", text)
    return match.group(1).strip() if match else "unversioned"


def _safe_backup_locator(value: object) -> dict[str, object] | None:
    """Return a detached logical locator or reject the complete object."""
    if not isinstance(value, Mapping):
        return None
    allowed = {"root_id", "name", "relative_path", "relative_paths"}
    if not value or not set(value).issubset(allowed):
        return None
    root_id = value.get("root_id")
    name = value.get("name")
    if (
        not isinstance(root_id, str)
        or re.fullmatch(r"[A-Za-z0-9._/-]+", root_id) is None
        or root_id.startswith(("/", "\\"))
        or ".." in root_id.split("/")
        or not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or ":" in name
    ):
        return None

    def safe_relative(relative: object) -> bool:
        if not isinstance(relative, str) or not relative:
            return False
        normalized = relative.replace("\\", "/")
        return (
            not normalized.startswith("/")
            and re.match(r"^[A-Za-z]:", normalized) is None
            and ".." not in normalized.split("/")
        )

    locator: dict[str, object] = {"root_id": root_id, "name": name}
    if "relative_path" in value:
        relative_path = value["relative_path"]
        if not safe_relative(relative_path):
            return None
        locator["relative_path"] = str(relative_path).replace("\\", "/")
    if "relative_paths" in value:
        relative_paths = value["relative_paths"]
        if (
            not isinstance(relative_paths, list)
            or not relative_paths
            or not all(safe_relative(item) for item in relative_paths)
        ):
            return None
        locator["relative_paths"] = [
            str(item).replace("\\", "/") for item in relative_paths
        ]
    return locator


def _synthetic_contract_sample(path: Path) -> None:
    """Write a minimal non-user contract fixture for structural validation."""
    document = Document()
    document.add_paragraph(
        "This contract is made between the influencer Health Old Creator "
        "and Varla / the advertiser. Both parties acknowledge the terms."
    )
    document.add_paragraph(
        "The influencer will receive 1 Varla electric dirt bike."
    )
    document.add_paragraph("Use relevant hashtags such as #Varla #M5S.")
    for text in (
        "Full Name: Health Old Creator",
        "Shipping Address: Health Old Address",
        "Phone Number: 000-000-0000",
        "Code Name: HEALTHOLD 1% (Valid for 2 months)",
        "Impact ID Number: HEALTH-OLD-ID",
        "Signature of the Influencer:",
        "Date: January 1, 2000",
    ):
        document.add_paragraph(text)
    table = document.add_table(rows=3, cols=2)
    rows = (
        ("Bike / Product Model", "1 Varla M5S"),
        ("Collaborating Creator", "Health Old Creator"),
        (
            "Signing Party / Influencer",
            "Health Old Creator / health-old@example.invalid",
        ),
    )
    for row, (label, value) in zip(table.rows, rows, strict=True):
        row.cells[0].text = label
        row.cells[1].text = value
    document.save(path)


class SkillHealthChecker:
    """Run each child check independently and disable only that child on failure."""

    def __init__(
        self,
        *,
        skills_root: str | Path | None = None,
        reply_project_root: str | Path | None = None,
        python_executable: str | Path | None | object = _AUTO,
        node_executable: str | Path | None | object = _AUTO,
        contract_output_root: str | Path | None = None,
        gmail_credentials: GmailCredentials | None = None,
        runner: Runner | None = None,
        clock: Clock | None = None,
        lock_path: str | Path | None = None,
        checkers: Mapping[str, Checker] | None = None,
    ) -> None:
        self.skills_root = (
            Path(skills_root)
            if skills_root is not None
            else Path.home() / ".codex" / "skills"
        )
        self.reply_project_root = (
            Path(reply_project_root)
            if reply_project_root is not None
            else _default_reply_root()
        )
        self.python_executable = (
            _resolve_python()
            if python_executable is _AUTO
            else (
                None
                if python_executable is None
                else str(python_executable)
            )
        )
        self.node_executable = (
            _resolve_node()
            if node_executable is _AUTO
            else (
                None if node_executable is None else str(node_executable)
            )
        )
        self.contract_output_root = (
            Path(contract_output_root)
            if contract_output_root is not None
            else Path.cwd() / "data" / "contract-previews"
        )
        self.gmail_credentials = gmail_credentials
        self.runner = runner or subprocess.run
        self.clock = clock or (lambda: datetime.now(UTC))
        self.lock_path = Path(lock_path) if lock_path is not None else None
        self._custom_checkers = dict(checkers) if checkers is not None else None

    def _run_command(self, argv: list[str]) -> None:
        try:
            completed = self.runner(
                argv,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("child skill check timed out") from exc
        except OSError as exc:
            raise RuntimeError(sanitize_error(exc)) from exc
        if getattr(completed, "returncode", 1) != 0:
            detail = sanitize_error(
                getattr(completed, "stderr", "")
                or getattr(completed, "stdout", "")
            )
            raise RuntimeError(f"child skill check failed: {detail}")

    def _skill_files(self, name: str, script: str) -> tuple[Path, Path]:
        root = self.skills_root / name
        skill_md = root / "SKILL.md"
        key_script = root / script
        if not skill_md.is_file() or not key_script.is_file():
            raise FileNotFoundError("required child skill file is unavailable")
        return skill_md, key_script

    def _check_gmail(self) -> HealthStatus:
        name = "varla-gmail-automation"
        if (
            self.gmail_credentials is not None
            and self.gmail_credentials.expected_account != EXPECTED_ACCOUNT
        ):
            return HealthStatus(
                name=name,
                status="misconfigured",
                enabled=False,
                version=self._safe_version(name),
                checks={},
                error=(
                    "Gmail expected account must be exactly "
                    "info@varlascooter.com"
                ),
            )
        if self.python_executable is None:
            return self._unavailable(name, "Python runtime is unavailable")
        skill_md, script = self._skill_files(
            name, "scripts/gmail_automation.py"
        )
        checks: dict[str, str] = {}
        self._run_command(
            [self.python_executable, "-m", "py_compile", str(script)]
        )
        checks["py_compile"] = "ok"
        self._run_command([self.python_executable, str(script), "--help"])
        checks["help"] = "ok"
        if (
            self.gmail_credentials is not None
            and self.gmail_credentials.configured
        ):
            credentials = self.gmail_credentials
            self._run_command(
                [
                    self.python_executable,
                    str(script),
                    "--credentials",
                    str(credentials.credentials_path),
                    "--token",
                    str(credentials.token_path),
                    "--expected-account",
                    credentials.expected_account,
                    "verify",
                ]
            )
            checks["verify"] = "ok"
        else:
            checks["verify"] = "skipped_not_configured"
        return HealthStatus(
            name=name,
            status="ok",
            enabled=True,
            version=_version(skill_md),
            checks=checks,
        )

    def _check_contract(self) -> HealthStatus:
        name = "varla-kol-contract-updater"
        if self.python_executable is None:
            return self._unavailable(name, "Python runtime is unavailable")
        skill_md, script = self._skill_files(
            name, "scripts/update_contract.py"
        )
        checks: dict[str, str] = {}
        self._run_command(
            [self.python_executable, "-m", "py_compile", str(script)]
        )
        checks["py_compile"] = "ok"
        self._run_command([self.python_executable, str(script), "--help"])
        checks["help"] = "ok"
        self.contract_output_root.mkdir(parents=True, exist_ok=True)
        sample = (
            self.contract_output_root
            / f".contract-health-sample-{uuid4().hex}.docx"
        )
        try:
            _synthetic_contract_sample(sample)
            gateway = ContractGateway(
                python_executable=self.python_executable,
                script_path=script,
                output_root=self.contract_output_root,
                runner=self.runner,
            )
            preview = gateway.preview(
                sample,
                name="Health Check Creator",
                email="health-check@example.invalid",
                rate="0%",
                agreement_date="July 29, 2026",
                bike_model="Varla M7S",
                retain_output=False,
            )
            if not preview.structure_unchanged:
                raise RuntimeError("contract dry-run structure check failed")
        finally:
            sample.unlink(missing_ok=True)
        checks["sample_copy"] = "ok"
        return HealthStatus(
            name=name,
            status="ok",
            enabled=True,
            version=_version(skill_md),
            checks=checks,
        )

    def _check_reply(self) -> HealthStatus:
        name = "varla-kol-reply-assistant"
        skill_md = self.skills_root / name / "SKILL.md"
        if not skill_md.is_file():
            raise FileNotFoundError("required child skill file is unavailable")
        if self.node_executable is None:
            return self._unavailable(name, "Node.js runtime is unavailable")
        if self.reply_project_root is None:
            return self._unavailable(
                name, "reply assistant project is unavailable"
            )

        js_files = (
            "chrome-extension/contentScript.js",
            "chrome-extension/popup.js",
            "src/app.js",
            "src/stageRules.js",
        )
        json_files = (
            "chrome-extension/manifest.json",
            "knowledge_seed/templates.json",
            "knowledge_seed/product_specs.json",
        )
        checks: dict[str, str] = {}
        for relative in js_files:
            path = self.reply_project_root / relative
            if not path.is_file():
                raise FileNotFoundError(
                    f"reply assistant file is unavailable: {relative}"
                )
            self._run_command(
                [self.node_executable, "--check", str(path)]
            )
            checks[f"node_check:{relative}"] = "ok"
        for relative in json_files:
            path = self.reply_project_root / relative
            if not path.is_file():
                raise FileNotFoundError(
                    f"reply assistant file is unavailable: {relative}"
                )
            with path.open("r", encoding="utf-8") as stream:
                json.load(stream)
            checks[f"json:{relative}"] = "ok"
        return HealthStatus(
            name=name,
            status="ok",
            enabled=True,
            version=_version(skill_md),
            checks=checks,
        )

    @staticmethod
    def _unavailable(name: str, error: str) -> HealthStatus:
        return HealthStatus(
            name=name,
            status="unavailable",
            enabled=False,
            version="unknown",
            checks={},
            error=error,
        )

    def _default_checkers(self) -> dict[str, Checker]:
        return {
            "varla-gmail-automation": self._check_gmail,
            "varla-kol-contract-updater": self._check_contract,
            "varla-kol-reply-assistant": self._check_reply,
        }

    def run(self) -> dict[str, HealthStatus]:
        checkers = self._custom_checkers or self._default_checkers()
        report: dict[str, HealthStatus] = {}
        previous = self._load_lock()
        lock_structure_trusted = self._lock_structure_trusted(previous)
        for name in SKILL_NAMES:
            checker = checkers.get(name)
            if checker is None:
                report[name] = self._unavailable(
                    name, "health checker is unavailable"
                )
                continue
            trust = (
                self._trust_state(name, previous)
                if lock_structure_trusted
                else "untrusted"
            )
            if trust != "trusted":
                report[name] = HealthStatus(
                    name=name,
                    status=trust,
                    enabled=False,
                    version=self._safe_version(name),
                    checks={},
                    error=(
                        "child skill hashes are not trusted; "
                        "manual lock acceptance is required"
                    ),
                    drift=trust == "drift",
                )
                continue
            try:
                status = checker()
                if status.name != name:
                    status = replace(status, name=name)
                status = replace(
                    status,
                    drift=self._has_drift(name, previous),
                )
                report[name] = status
            except Exception as exc:
                report[name] = HealthStatus(
                    name=name,
                    status="failed",
                    enabled=False,
                    version=self._safe_version(name),
                    checks={},
                    error=sanitize_error(exc),
                    drift=self._has_drift(name, previous),
                )
        return report

    def _safe_version(self, name: str) -> str:
        try:
            return _version(self.skills_root / name / "SKILL.md")
        except (OSError, UnicodeError):
            return "unknown"

    def _load_lock(self) -> dict[str, Any]:
        if self.lock_path is None or not self.lock_path.is_file():
            return {}
        try:
            payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _file_specs(self, name: str) -> list[tuple[str, str, Path]]:
        specs: dict[str, list[tuple[str, str, Path]]] = {
            "varla-gmail-automation": [
                (
                    "skill_root",
                    "SKILL.md",
                    self.skills_root / name / "SKILL.md",
                ),
                (
                    "skill_root",
                    "scripts/gmail_automation.py",
                    self.skills_root
                    / name
                    / "scripts"
                    / "gmail_automation.py",
                ),
            ],
            "varla-kol-contract-updater": [
                (
                    "skill_root",
                    "SKILL.md",
                    self.skills_root / name / "SKILL.md",
                ),
                (
                    "skill_root",
                    "scripts/update_contract.py",
                    self.skills_root
                    / name
                    / "scripts"
                    / "update_contract.py",
                ),
            ],
            "varla-kol-reply-assistant": [
                (
                    "skill_root",
                    "SKILL.md",
                    self.skills_root / name / "SKILL.md",
                ),
            ],
        }
        if name == "varla-kol-reply-assistant" and self.reply_project_root:
            for relative in (
                "chrome-extension/contentScript.js",
                "chrome-extension/popup.js",
                "src/app.js",
                "src/stageRules.js",
                "chrome-extension/manifest.json",
                "knowledge_seed/templates.json",
                "knowledge_seed/product_specs.json",
            ):
                specs[name].append(
                    (
                        "reply_project_root",
                        relative,
                        self.reply_project_root / relative,
                    )
                )
        return specs[name]

    def _current_files(self, name: str) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        for root_id, relative, path in self._file_specs(name):
            if path.is_file():
                files.append(
                    {
                        "root_id": root_id,
                        "relative_path": relative.replace("\\", "/"),
                        "sha256": _sha256(path),
                    }
                )
        return files

    def _has_drift(self, name: str, lock: Mapping[str, Any]) -> bool:
        return (
            self._lock_structure_trusted(lock)
            and self._trust_state(name, lock) == "drift"
        )

    def _trust_state(self, name: str, lock: Mapping[str, Any]) -> str:
        if not self._lock_structure_trusted(lock):
            return "untrusted"
        skills = lock.get("skills")
        entry = skills.get(name) if isinstance(skills, Mapping) else None
        locked_files = entry.get("files") if isinstance(entry, Mapping) else None
        if not isinstance(locked_files, list) or not locked_files:
            return "untrusted"
        return (
            "trusted"
            if locked_files == self._current_files(name)
            else "drift"
        )

    def accept_verified_updates(self) -> dict[str, HealthStatus]:
        """Validate drifted children, then atomically trust only stable files."""
        if self.lock_path is None:
            raise ValueError("lock path is not configured")
        previous = self._load_lock()
        if not self._lock_structure_trusted(previous):
            raise RuntimeError("trusted child skill lock is required")

        checkers = self._custom_checkers or self._default_checkers()
        accepted: dict[str, tuple[HealthStatus, list[dict[str, str]]]] = {}
        for name in SKILL_NAMES:
            trust = self._trust_state(name, previous)
            if trust == "trusted":
                continue
            if trust != "drift":
                raise RuntimeError("child skill lock cannot be accepted")
            checker = checkers.get(name)
            if checker is None:
                raise RuntimeError(f"{name} validation is unavailable")
            before = self._current_files(name)
            if len(before) != len(self._file_specs(name)):
                raise RuntimeError(f"{name} required files are unavailable")
            try:
                status = checker()
            except Exception as exc:
                raise RuntimeError(
                    f"{name} validation failed: {sanitize_error(exc)}"
                ) from exc
            if status.name != name:
                status = replace(status, name=name)
            if status.status != "ok" or not status.enabled:
                raise RuntimeError(f"{name} validation did not pass")
            after = self._current_files(name)
            if after != before:
                raise RuntimeError(f"{name} changed during validation")
            accepted[name] = (status, before)

        if not accepted:
            return self.run()

        checked_at = self.clock()
        if checked_at.tzinfo is None:
            raise ValueError("clock must return timezone-aware timestamps")
        timestamp = checked_at.astimezone(UTC).isoformat(timespec="seconds")
        payload = json.loads(json.dumps(previous))
        payload["checked_at"] = timestamp
        for name, (status, files) in accepted.items():
            entry = payload["skills"][name]
            entry.update(
                {
                    "version": status.version,
                    "checked_at": timestamp,
                    "status": "ok",
                    "enabled": True,
                    "drift": False,
                    "files": files,
                }
            )

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.lock_path.with_name(
            f".{self.lock_path.name}.{uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _replace_with_bounded_retry(temporary, self.lock_path)
        return self.run()

    @staticmethod
    def _historical_hashes_valid(value: object) -> bool:
        if not isinstance(value, Mapping):
            return False
        return all(
            isinstance(relative, str)
            and bool(relative)
            and not relative.startswith(("/", "\\"))
            and re.match(r"^[A-Za-z]:", relative) is None
            and ".." not in relative.replace("\\", "/").split("/")
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-fA-F]{64}", digest) is not None
            for relative, digest in value.items()
        )

    def _entry_structure_trusted(
        self,
        name: str,
        entry: object,
    ) -> bool:
        if not isinstance(entry, Mapping):
            return False
        allowed = {
            "baseline_sha256",
            "updated_sha256",
            "backup_protection",
            "backup",
            "installed_root_id",
            "version",
            "checked_at",
            "status",
            "enabled",
            "drift",
            "files",
        }
        if not set(entry).issubset(allowed):
            return False
        if entry.get("installed_root_id") != f"codex_skills/{name}":
            return False
        preserved = self._preserved_lock_files(entry)
        expected = {
            (root_id, relative.replace("\\", "/"))
            for root_id, relative, _path in self._file_specs(name)
        }
        actual = {
            (item["root_id"], item["relative_path"]) for item in preserved
        }
        if not preserved or actual != expected or len(actual) != len(preserved):
            return False
        for field in ("baseline_sha256", "updated_sha256"):
            if field in entry and not self._historical_hashes_valid(
                entry[field]
            ):
                return False
        if "backup" in entry and _safe_backup_locator(entry["backup"]) is None:
            return False
        if "backup_protection" in entry and not isinstance(
            entry["backup_protection"], Mapping
        ):
            return False
        return True

    def _lock_structure_trusted(self, lock: Mapping[str, Any]) -> bool:
        if lock.get("schema_version") != 2:
            return False
        skills = lock.get("skills")
        return isinstance(skills, Mapping) and all(
            self._entry_structure_trusted(name, skills.get(name))
            for name in SKILL_NAMES
        )

    @staticmethod
    def _preserved_lock_files(entry: Mapping[str, Any]) -> list[dict[str, str]]:
        files = entry.get("files")
        if not isinstance(files, list):
            return []
        preserved: list[dict[str, str]] = []
        for item in files:
            if (
                not isinstance(item, Mapping)
                or set(item) != {"root_id", "relative_path", "sha256"}
            ):
                return []
            root_id = item.get("root_id")
            relative = item.get("relative_path")
            sha256 = item.get("sha256")
            if (
                not isinstance(root_id, str)
                or root_id not in {"skill_root", "reply_project_root"}
                or not isinstance(relative, str)
                or not relative
                or relative.startswith(("/", "\\"))
                or re.match(r"^[A-Za-z]:", relative) is not None
                or ".." in relative.replace("\\", "/").split("/")
                or not isinstance(sha256, str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is None
            ):
                return []
            preserved.append(
                {
                    "root_id": root_id,
                    "relative_path": relative.replace("\\", "/"),
                    "sha256": sha256.lower(),
                }
            )
        return preserved

    def write_lock(self, report: Mapping[str, HealthStatus]) -> None:
        if self.lock_path is None:
            raise ValueError("lock path is not configured")
        previous = self._load_lock()
        previous_skills = previous.get("skills")
        previous_skills = (
            previous_skills if isinstance(previous_skills, Mapping) else {}
        )
        previous_trusted = self._lock_structure_trusted(previous)
        checked_at = self.clock()
        if checked_at.tzinfo is None:
            raise ValueError("clock must return timezone-aware timestamps")

        skills: dict[str, Any] = {}
        for name in SKILL_NAMES:
            old = previous_skills.get(name)
            old = old if isinstance(old, Mapping) else {}
            entry: dict[str, Any] = {}
            if previous_trusted:
                for key in (
                    "baseline_sha256",
                    "updated_sha256",
                    "backup_protection",
                ):
                    if key in old:
                        entry[key] = old[key]
                safe_backup = _safe_backup_locator(old.get("backup"))
                if safe_backup is not None:
                    entry["backup"] = safe_backup
            status = report[name]
            entry.update(
                {
                    "installed_root_id": f"codex_skills/{name}",
                    "version": status.version,
                    "checked_at": checked_at.astimezone(UTC).isoformat(
                        timespec="seconds"
                    ),
                    "status": status.status,
                    "enabled": status.enabled,
                    "drift": status.drift,
                    # Observed drift is never promoted to a trusted baseline.
                    # A future explicit human acceptance flow owns that change.
                    "files": (
                        self._preserved_lock_files(old)
                        if previous_trusted
                        else []
                    ),
                }
            )
            skills[name] = entry

        payload = {
            "schema_version": 2,
            "checked_at": checked_at.astimezone(UTC).isoformat(
                timespec="seconds"
            ),
            "skills": skills,
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.lock_path.with_name(
            f".{self.lock_path.name}.{uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _replace_with_bounded_retry(temporary, self.lock_path)


__all__ = [
    "GmailCredentials",
    "HealthStatus",
    "SkillHealthChecker",
]
