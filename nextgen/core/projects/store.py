from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.governance.contracts import DataContract, DataQualityRule

_PROJECT_SCHEMA_VERSION = 2
_MAX_PROJECT_ARCHIVE_BYTES = 512 * 1024 * 1024
_REQUIRED_ARCHIVE_MEMBERS = frozenset({"manifest.json", "dataset/data.parquet"})


class ProjectStoreError(ValueError):
    """User-safe failure for corrupt, incompatible or invalid local project files."""


@dataclass(frozen=True)
class ProjectSnapshot:
    path: Path
    project_id: str
    app_version: str
    locale: str
    frame: pd.DataFrame
    contract: DataContract
    schema_version: int


class ProjectStore:
    """Versioned, local `.dsproj` persistence with atomic replacement and backup.

    The archive uses Parquet for tabular values and JSON for metadata. It intentionally
    avoids pickle and rejects unexpectedly large or malformed archives before loading.
    """

    def __init__(self, project_dir: Path, *, max_archive_bytes: int = _MAX_PROJECT_ARCHIVE_BYTES) -> None:
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.max_archive_bytes = max_archive_bytes

    def save(
        self,
        path: str | Path,
        frame: pd.DataFrame,
        contract: DataContract,
        *,
        project_id: str | None = None,
        app_version: str = "0.1.0-alpha",
        locale: str = "en-US",
    ) -> Path:
        self._validate_frame(frame)
        destination = self._resolve_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest(
            project_id=project_id or self._existing_project_id(destination) or str(uuid.uuid4()),
            app_version=app_version,
            locale=locale,
            contract=contract,
        )
        with tempfile.TemporaryDirectory(prefix="datasense-project-") as folder:
            staging = Path(folder)
            data_path = staging / "data.parquet"
            manifest_path = staging / "manifest.json"
            frame.to_parquet(data_path, index=False)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            archive_path = self._archive_staged_project(staging, destination.parent)
            self._backup_existing(destination)
            os.replace(archive_path, destination)
        return destination

    def load(self, path: str | Path) -> ProjectSnapshot:
        source = self._resolve_path(path)
        if not source.exists():
            raise ProjectStoreError(f"Project not found: {source.name}")
        if source.stat().st_size > self.max_archive_bytes:
            raise ProjectStoreError("Project archive exceeds the configured local size limit.")
        try:
            with zipfile.ZipFile(source, "r") as archive:
                names = frozenset(archive.namelist())
                if not _REQUIRED_ARCHIVE_MEMBERS.issubset(names):
                    raise ProjectStoreError("Project archive is missing required members.")
                if archive.testzip() is not None:
                    raise ProjectStoreError("Project archive failed integrity verification.")
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                migrated = self._migrate_manifest(manifest)
                parquet_bytes = archive.read("dataset/data.parquet")
        except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectStoreError("Project could not be read. It may be corrupted or incompatible.") from exc

        try:
            frame = pd.read_parquet(io.BytesIO(parquet_bytes))
        except Exception as exc:  # pyarrow exceptions vary by version
            raise ProjectStoreError("Project dataset could not be decoded from Parquet.") from exc
        self._validate_frame(frame)
        contract = self._contract_from_manifest(migrated)
        return ProjectSnapshot(
            path=source,
            project_id=migrated["project_id"],
            app_version=migrated["app_version"],
            locale=migrated["locale"],
            frame=frame,
            contract=contract,
            schema_version=migrated["schema_version"],
        )

    def backup_path(self, path: str | Path) -> Path:
        destination = self._resolve_path(path)
        return destination.with_suffix(destination.suffix + ".bak")

    def _resolve_path(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.project_dir / candidate
        if candidate.suffix.lower() != ".dsproj" and not candidate.name.lower().endswith(".dsproj.bak"):
            candidate = candidate.with_suffix(".dsproj")
        return candidate

    def _manifest(self, *, project_id: str, app_version: str, locale: str, contract: DataContract) -> dict[str, Any]:
        return {
            "schema_version": _PROJECT_SCHEMA_VERSION,
            "project_id": project_id,
            "app_version": app_version,
            "locale": locale,
            "contract": {
                "name": contract.name,
                "rules": [
                    {"rule_type": rule.rule_type, "column": rule.column, "severity": rule.severity}
                    for rule in contract.rules
                ],
            },
        }

    def _archive_staged_project(self, staging: Path, destination_dir: Path) -> Path:
        fd, archive_name = tempfile.mkstemp(prefix="datasense-", suffix=".tmp", dir=destination_dir)
        os.close(fd)
        archive_path = Path(archive_name)
        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(staging / "data.parquet", "dataset/data.parquet")
                archive.write(staging / "manifest.json", "manifest.json")
            return archive_path
        except Exception:
            archive_path.unlink(missing_ok=True)
            raise

    def _backup_existing(self, destination: Path) -> None:
        if destination.exists():
            shutil.copy2(destination, self.backup_path(destination))

    def _existing_project_id(self, destination: Path) -> str | None:
        if not destination.exists():
            return None
        try:
            return self.load(destination).project_id
        except ProjectStoreError:
            # Preserve the original as backup on the next successful save but avoid
            # using its malformed metadata as a new project's identity.
            return None

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("ProjectStore expects a pandas DataFrame.")
        if frame.empty:
            raise ProjectStoreError("Projects cannot be saved with an empty dataset.")
        if frame.columns.empty or frame.columns.has_duplicates:
            raise ProjectStoreError("Project datasets require unique, non-empty columns.")

    @staticmethod
    def _migrate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
        version = manifest.get("schema_version")
        if version == 1:
            return {
                "schema_version": 1,
                "project_id": manifest.get("project_id", "legacy-project"),
                "app_version": manifest.get("app_version", "unknown"),
                "locale": manifest.get("locale", "en-US"),
                "contract": {
                    "name": manifest.get("contract_name", "Imported legacy contract"),
                    "rules": [],
                },
            }
        if version != _PROJECT_SCHEMA_VERSION:
            raise ProjectStoreError(f"Unsupported project schema version: {version}")
        required = {"project_id", "app_version", "locale", "contract"}
        if not required.issubset(manifest):
            raise ProjectStoreError("Project manifest is missing required metadata.")
        return manifest

    @staticmethod
    def _contract_from_manifest(manifest: dict[str, Any]) -> DataContract:
        contract_data = manifest["contract"]
        if not isinstance(contract_data, dict) or not isinstance(contract_data.get("rules", []), list):
            raise ProjectStoreError("Project contract metadata is invalid.")
        try:
            rules = tuple(
                DataQualityRule(rule["rule_type"], rule["column"], rule.get("severity", "high"))
                for rule in contract_data["rules"]
            )
            return DataContract(contract_data["name"], rules)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectStoreError("Project contract could not be reconstructed.") from exc
