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
