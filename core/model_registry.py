"""Local model registry for reproducible, reviewable DataSense model artifacts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_SCHEMA = "datasense.model-registry/v1"


@dataclass(frozen=True)
class ModelRecord:
    name: str
    version: str
    task: str
    target: str
    features: tuple[str, ...]
    model_path: str
    dataset_fingerprint: str
    metrics: dict[str, Any] = field(default_factory=dict)
    status: str = "candidate"
    created_at: str = ""
    artifact_sha256: str = ""

    def fingerprint(self) -> str:
        payload = asdict(self)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


@dataclass
class ModelRegistry:
    """Filesystem-backed registry; registry metadata never contains dataset rows."""

    path: str = "models/registry.json"
    records: list[ModelRecord] = field(default_factory=list)

    def load(self) -> "ModelRegistry":
        target = Path(self.path)
        if not target.exists():
            return self
        payload = json.loads(target.read_text(encoding="utf-8"))
        if payload.get("schema") != REGISTRY_SCHEMA:
            raise ValueError("Unsupported model registry schema.")
        self.records = [ModelRecord(**item) for item in payload.get("records", [])]
        return self

    def save(self) -> None:
        target = Path(self.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": REGISTRY_SCHEMA, "records": [asdict(item) for item in self.records]}
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    def register(
        self,
        *,
        name: str,
        version: str,
        task: str,
        target: str,
        features: list[str],
        model_path: str,
        dataset_fingerprint: str,
        metrics: dict[str, Any] | None = None,
        status: str = "candidate",
    ) -> ModelRecord:
        if not name.strip() or not version.strip():
            raise ValueError("Model name and version are required.")
        if status not in {"candidate", "approved", "retired"}:
            raise ValueError("Invalid model lifecycle status.")
        path = Path(model_path)
        if not path.exists():
            raise ValueError("Model artifact does not exist.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        record = ModelRecord(
            name=name.strip(), version=version.strip(), task=task.strip(), target=target,
            features=tuple(features), model_path=str(path), dataset_fingerprint=dataset_fingerprint,
            metrics=dict(metrics or {}), status=status,
            created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            artifact_sha256=digest,
        )
        self.records = [r for r in self.records if not (r.name == record.name and r.version == record.version)]
        self.records.append(record)
        self.save()
        return record

    def approve(self, name: str, version: str) -> ModelRecord:
        matches = [r for r in self.records if r.name == name and r.version == version]
        if not matches:
            raise KeyError(f"Model {name}:{version} is not registered.")
        selected = matches[-1]
        updated = ModelRecord(**{**asdict(selected), "status": "approved"})
        self.records = [updated if r is selected else r for r in self.records]
        self.save()
        return updated

    def latest(self, name: str, approved_only: bool = False) -> ModelRecord | None:
        matches = [r for r in self.records if r.name == name and (not approved_only or r.status == "approved")]
        if not matches:
            return None
        return sorted(matches, key=lambda r: (r.created_at, r.version))[-1]

    def verify_artifact(self, record: ModelRecord) -> bool:
        path = Path(record.model_path)
        if not path.exists():
            return False
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest == record.artifact_sha256

    def as_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name,
                "version": r.version,
                "task": r.task,
                "target": r.target,
                "status": r.status,
                "dataset_fingerprint": r.dataset_fingerprint,
                "artifact_sha256": r.artifact_sha256,
            }
            for r in self.records
        ]
