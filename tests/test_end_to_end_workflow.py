"""End-to-end integration checks for the local-first DataSense workflow."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from core.automl import AutoML
from core.data_manager import DataManager
from core.evidence import build_evidence_payload, sign_evidence_payload, verify_evidence_bundle
from core.governance import DataContract, QualityGatePolicy, SchemaDriftPolicy, capture_schema, compare_schema
from core.project import load_project, save_project
from core.recipes import AnalysisRecipe, RecipeStep, execute_recipe


def _manager(tmp_path: Path) -> DataManager:
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=40, freq="D"),
            "units": np.arange(1, 41),
            "revenue": np.arange(10, 410, 10, dtype=float),
        }
    )
    path = tmp_path / "retail.csv"
    frame.to_csv(path, index=False)
    manager = DataManager()
    ok, message = manager.load(str(path))
    assert ok, message
    return manager


def test_full_preparation_recipe_project_roundtrip(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    recipe = AnalysisRecipe(
        name="retail-prep",
        steps=[RecipeStep("fill_missing", {"column": "revenue", "strategy": "median"})],
    )
    execute_recipe(manager, recipe)
    project = tmp_path / "analysis.dsproj"
    ok, message = save_project(manager, str(project))
    assert ok, message

    restored = DataManager()
    ok, message = load_project(restored, str(project))
    assert ok, message
    assert restored.columns == manager.columns
    assert len(restored.df) == len(manager.df)
    assert restored.lineage.summary() == manager.lineage.summary()


def test_governance_and_evidence_roundtrip(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    contract = DataContract()
    report = contract.evaluate(manager.df)
    baseline = capture_schema(manager.df)
    drift_policy = SchemaDriftPolicy()
    drift = compare_schema(baseline, capture_schema(manager.df), drift_policy)
    payload = build_evidence_payload(
        report=report,
        contract=contract,
        gate_policy=QualityGatePolicy(),
        quality_history=manager.quality_history,
        schema_baseline=baseline,
        schema_drift_policy=drift_policy,
        schema_drift_report=drift,
        lineage=manager.lineage,
        generated_at="2025-01-01T00:00:00+00:00",
    )
    bundle = sign_evidence_payload(payload, b"integration-secret", "test-key")
    encoded = json.loads(json.dumps(bundle))
    verified = verify_evidence_bundle(encoded, lambda key_id: b"integration-secret" if key_id == "test-key" else None)
    assert verified.valid
    assert verified.payload_digest


def test_automl_uses_time_aware_evaluation(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    automl = AutoML(manager.df, time_column="date")
    result = automl.run("revenue", features=["units"], test_size=0.2)
    assert result.candidates
    assert all(candidate.metadata["split_strategy"] == "chronological" for candidate in result.candidates)
    assert result.best in result.candidates
