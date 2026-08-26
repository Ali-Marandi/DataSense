from __future__ import annotations

import pandas as pd
import pytest

from core.analysis.contracts import ProcessingContext
from core.analysis.data_readiness import DataReadinessConfig, DataReadinessInsightsModule


def test_data_readiness_reports_healthy_dataset_without_warnings():
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B", "B", "C", "C"],
            "revenue": [100.0, 105.0, 102.0, 108.0, 103.0, 104.0],
        }
    )

    result = DataReadinessInsightsModule().process(frame, ProcessingContext())

    assert result.module_id == "data-readiness-insights/v1"
    assert result.summary["ready"] is True
    assert result.summary["readiness_score"] == 100
    assert result.summary["outlier_cells"] == 0
    assert result.warnings == ()


def test_data_readiness_reports_aggregate_quality_warnings_without_raw_values():
    frame = pd.DataFrame(
        {
            "customer_id": ["C-1", "C-2", "C-3", "C-4", "C-5", "C-6"],
            "revenue": [100.0, 101.0, None, 99.0, 100.0, 10_000.0],
            "category": ["x", None, "x", "y", "y", "z"],
        }
    )

    result = DataReadinessInsightsModule().process(frame, ProcessingContext())

    assert result.summary["columns_with_missing"] == 2
    assert result.summary["high_cardinality_columns"] == 1
    assert result.summary["outlier_cells"] == 1
    assert result.summary["readiness_score"] < 100
    joined_warnings = " ".join(result.warnings)
    assert "customer_id" in joined_warnings
    assert "revenue" in joined_warnings
    assert "C-1" not in joined_warnings
    assert "10_000" not in joined_warnings


def test_data_readiness_handles_empty_data_and_configuration_errors():
    empty = pd.DataFrame(columns=["revenue"])
    result = DataReadinessInsightsModule().process(empty, ProcessingContext())

    assert result.summary == {"ready": False, "rows": 0, "columns": 1}
    assert result.warnings == ("The active dataset has no rows to analyze.",)
    with pytest.raises(ValueError, match="IQR"):
        DataReadinessConfig(iqr_multiplier=0)
    with pytest.raises(ValueError, match="cardinality"):
        DataReadinessConfig(high_cardinality_ratio=1.1)
    with pytest.raises(TypeError, match="pandas DataFrame"):
        DataReadinessInsightsModule().process(["not-a-frame"], ProcessingContext())


def test_data_readiness_is_deterministic_and_does_not_mutate_input():
    frame = pd.DataFrame(
        {
            "z_identifier": ["z-1", "z-2", "z-3", "z-4"],
            "a_identifier": ["a-1", "a-2", "a-3", "a-4"],
            "amount": [10.0, 11.0, 12.0, 250.0],
        }
    )
    original = frame.copy(deep=True)
    module = DataReadinessInsightsModule()

    first = module.process(frame, ProcessingContext())
    second = module.process(frame, ProcessingContext())

    pd.testing.assert_frame_equal(frame, original)
    assert first == second
    assert first.warnings[0] == "High-cardinality columns may be identifiers: a_identifier, z_identifier."


def test_data_readiness_tracks_non_finite_values_without_exposing_cell_values():
    frame = pd.DataFrame({"metric": [1.0, 2.0, float("inf"), float("-inf"), 3.0, 4.0]})

    result = DataReadinessInsightsModule().process(frame, ProcessingContext())

    assert result.summary["non_finite_numeric_cells"] == 2
    assert result.summary["finite_numeric_observations"] == 4
    assert result.summary["numeric_columns_considered"] == 1
    assert any(warning.startswith("Non-finite numeric values detected in: metric (2).") for warning in result.warnings)
    assert "inf" not in " ".join(result.warnings).lower()


def test_data_readiness_uses_ratio_based_missingness_and_configurable_threshold():
    narrow = pd.DataFrame({"value": [1.0, None, 3.0, 4.0]})
    wide = pd.DataFrame({"value": [1.0, None, 3.0, 4.0], "a": [1, 2, 3, 4], "b": [1, 2, 3, 4]})

    narrow_score = DataReadinessInsightsModule().process(narrow, ProcessingContext()).summary["readiness_score"]
    wide_score = DataReadinessInsightsModule().process(wide, ProcessingContext()).summary["readiness_score"]
    strict = DataReadinessInsightsModule(DataReadinessConfig(readiness_threshold=100)).process(wide, ProcessingContext())

    assert wide_score > narrow_score
    assert strict.summary["ready"] is False
    with pytest.raises(ValueError, match="threshold"):
        DataReadinessConfig(readiness_threshold=101)


def test_data_readiness_rejects_duplicate_column_names():
    frame = pd.DataFrame([[1, 2], [3, 4]], columns=["amount", "amount"])

    with pytest.raises(ValueError, match="unique column names"):
        DataReadinessInsightsModule().process(frame, ProcessingContext())
