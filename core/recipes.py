"""Portable, allow-listed analysis recipes for repeatable DataSense workflows."""
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
        payload = {"name": self.name, "steps": [step.to_dict() for step in self.steps], "version": self.version}
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


def recipe_from_history(manager, name: str, description: str = "") -> AnalysisRecipe:
    """Create a conservative recipe from labelled mutation history.

    Only operations with an explicit parameter representation should be promoted automatically;
    free-form history labels are retained as human-readable notes rather than executable code.
    """
    supported = {"Dropped rows with missing values", "Dropped duplicate rows"}
    steps: list[RecipeStep] = []
    for item in manager.history[1:]:
        if item.label in supported:
            if item.label == "Dropped duplicate rows":
                steps.append(RecipeStep("drop_duplicates"))
            else:
                steps.append(RecipeStep("drop_missing"))
    return AnalysisRecipe(name=name, description=description, steps=steps)


def execute_recipe(manager, recipe: AnalysisRecipe) -> list[str]:
    """Execute only explicitly allow-listed DataManager operations."""
    handlers = {
        "drop_duplicates": lambda p: manager.drop_duplicates(p.get("subset")),
        "drop_missing": lambda p: manager.drop_missing(p.get("columns"), p.get("how", "any")),
        "fill_missing": lambda p: manager.fill_missing(p["column"], p.get("strategy", "mean"), p.get("value")),
        "remove_outliers": lambda p: manager.remove_outliers(p["column"], p.get("method", "iqr"), float(p.get("threshold", 1.5))),
        "scale_columns": lambda p: manager.scale_columns(list(p["columns"]), p.get("method", "standard")),
        "rename_column": lambda p: manager.rename_column(p["old"], p["new"]),
        "cast_column": lambda p: manager.cast_column(p["column"], p.get("dtype", "text")),
    }
    messages: list[str] = []
    for step in recipe.steps:
        if step.operation not in handlers:
            raise ValueError(f"Recipe operation '{step.operation}' is not allowed.")
        try:
            ok, message = handlers[step.operation](step.params)
        except KeyError as exc:
            raise ValueError(f"Recipe operation '{step.operation}' is missing parameter '{exc.args[0]}'.") from exc
        if not ok:
            raise ValueError(f"Recipe step '{step.operation}' failed: {message}")
        messages.append(message)
    return messages
