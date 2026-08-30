"""Persist trained models to .dsmodel bundles and score new data with them."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

MODEL_EXTENSION = ".dsmodel"


@dataclass
class ModelBundle:
    estimator: Any
    task: str
    target: str
    features: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    label: str = ""
    created: str = ""
    app_version: str = ""
    dataset_fingerprint: str = ""
    artifact_sha256: str = ""

    def describe(self) -> pd.DataFrame:
        rows = [
            {"property": "Label", "value": self.label},
            {"property": "Task", "value": self.task},
            {"property": "Target", "value": self.target},
            {"property": "Features", "value": ", ".join(self.features)},
            {"property": "Created", "value": self.created},
            {"property": "Built with", "value": self.app_version},
            {"property": "Dataset fingerprint", "value": self.dataset_fingerprint},
            {"property": "Artifact SHA-256", "value": self.artifact_sha256},
        ]
        rows += [{"property": k, "value": v} for k, v in self.metrics.items()]
        return pd.DataFrame(rows)


def save_model(path: str, bundle: ModelBundle) -> tuple[bool, str]:
    import joblib
    from .version import APP_VERSION

    if not path.endswith(MODEL_EXTENSION):
        path += MODEL_EXTENSION
    bundle.created = bundle.created or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    bundle.app_version = bundle.app_version or f"DataSense {APP_VERSION}"
    try:
        bundle.artifact_sha256 = ""
        joblib.dump(bundle, path)
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        # The digest is tracked in the registry; embedding it in the pickle would make the
        # artifact self-referential. Keep the ModelBundle field available for registry export.
        bundle.artifact_sha256 = digest
    except Exception as exc:
        return False, str(exc)
    return True, f"Model saved to {os.path.basename(path)}"


def load_model(path: str) -> tuple[ModelBundle | None, str]:
    import joblib

    try:
        bundle = joblib.load(path)
    except Exception as exc:
        return None, str(exc)
    if not isinstance(bundle, ModelBundle):
        return None, "This file is not a DataSense model bundle."
    return bundle, f"Loaded model '{bundle.label or bundle.target}'"


def score(bundle: ModelBundle, df: pd.DataFrame, output: str = "prediction") -> tuple[pd.DataFrame | None, str]:
    missing = [c for c in bundle.features if c not in df.columns]
    if missing:
        return None, f"Dataset is missing required feature(s): {', '.join(missing)}"
    features = df[bundle.features].copy()
    for col in features.columns:
        if not pd.api.types.is_numeric_dtype(features[col]):
            features[col] = pd.factorize(features[col])[0]
    features = features.replace([float("inf"), float("-inf")], pd.NA)
    features = features.fillna(features.mean(numeric_only=True)).fillna(0)
    try:
        predictions = bundle.estimator.predict(features)
    except Exception as exc:
        return None, str(exc)
    out = df.copy()
    out[output] = predictions
    return out, f"Scored {len(out):,} row(s)."
