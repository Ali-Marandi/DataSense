from __future__ import annotations

import pandas as pd

from core.analysis.contracts import ProcessingContext
from core.analysis.time_series import TimeSeriesDiagnosticsModule


def test_time_series_diagnostics_reports_numeric_and_timestamp_readiness():
    frame = pd.DataFrame(
        {
            "at": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "value": [100.0, 110.0, 105.0],
        }
    )

    result = TimeSeriesDiagnosticsModule("value", "at").process(frame, ProcessingContext())

    assert result.summary["ready"] is True
    assert result.summary["valid_observations"] == 3
    assert result.summary["mean"] == 105.0
    assert result.summary["timestamp_ready"] is True
    assert result.warnings == ()


def test_time_series_diagnostics_flags_missing_columns_and_data_quality_problems():
    missing_result = TimeSeriesDiagnosticsModule("value").process(pd.DataFrame({"other": [1]}), ProcessingContext())
    assert missing_result.summary["ready"] is False
    assert "missing" in missing_result.warnings[0]

    frame = pd.DataFrame({"at": ["2026-01-02", "2026-01-01", "bad"], "value": ["10", None, "not-a-number"]})
    result = TimeSeriesDiagnosticsModule("value", "at").process(frame, ProcessingContext())

    assert result.summary["valid_observations"] == 1
    assert result.summary["timestamp_ready"] is False
    assert any("timestamp" in warning.lower() for warning in result.warnings)
