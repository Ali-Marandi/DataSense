"""Portable analysis recipes for repeatable DataSense workflows."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .version import APP_VERSION


@dataclass(frozen=True)
class RecipeStep:
    operation: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisRecipe:
    name: str
    steps: list[RecipeStep] = field(default_factory=list)
    description: str = ""
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    app_version: str = APP_VERSION

    @property
    def fingerprint(self) -> str:
        payload = {
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
            "version": self.version,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "datasense.analysis-recipe/v1",
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at,
            "app_version": self.app_version,
            "fingerprint": self.fingerprint,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AnalysisRecipe":
        if value.get("schema") not in (None, "datasense.analysis-recipe/v1"):
            raise ValueError("Unsupported analysis recipe schema.")
        return cls(
            name=str(value.get("name", "Unnamed recipe")),
            description=str(value.get("description", "")),
            version=int(value.get("version", 1)),
            created_at=str(value.get("created_at", datetime.now(timezone.utc).replace(microsecond=0).isoformat())),
            app_version=str(value.get("app_version", APP_VERSION)),
            steps=[RecipeStep(str(item.get("operation", "")), dict(item.get("params", {}) or {})) for item in value.get("steps", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)

    @classmethod
    def from_json(cls, payload: str) -> "AnalysisRecipe":
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError("Recipe root must be a JSON object.")
        return cls.from_dict(value)
