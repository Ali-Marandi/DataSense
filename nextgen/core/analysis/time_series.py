from __future__ import annotations

import math

import pandas as pd

from core.analysis.contracts import ProcessingContext, ProcessingResult


class TimeSeriesDiagnosticsModule:
    """Descriptive local diagnostics for a numeric series.

    The module measures data readiness and summary statistics. It deliberately does
    not produce trading signals, price targets, portfolio weights, or execution advice.
    """

    module_id = "time-series-diagnostics/v1"

    def __init__(self, value_column: str, timestamp_column: str | None = None) -> None:
        if not value_column.strip():
            raise ValueError("A value column is required for time-series diagnostics.")
        self.value_column = value_column
        self.timestamp_column = timestamp_column

    def process(self, frame: pd.DataFrame, context: ProcessingContext) -> ProcessingResult:
        if self.value_column not in frame.columns:
            return ProcessingResult(
                module_id=self.module_id,
                summary={"ready": False, "valid_observations": 0},
                warnings=(f"Required value column '{self.value_column}' is missing.",),
            )

        numeric_values = pd.to_numeric(frame[self.value_column], errors="coerce").dropna()
        total_rows = len(frame)
        valid_count = len(numeric_values)
        warnings: list[str] = []
        if valid_count == 0:
            warnings.append("No numeric observations are available after local coercion.")
        if valid_count < 3:
            warnings.append("At least three numeric observations are recommended for variance diagnostics.")

        summary: dict[str, int | float | str | bool] = {
            "ready": valid_count >= 3,
            "total_rows": total_rows,
            "valid_observations": valid_count,
            "missing_or_non_numeric": total_rows - valid_count,
        }
        if valid_count:
            summary.update(
                {
                    "minimum": float(numeric_values.min()),
                    "maximum": float(numeric_values.max()),
                    "mean": float(numeric_values.mean()),
                    "standard_deviation": float(numeric_values.std(ddof=1)) if valid_count > 1 else 0.0,
                }
            )

        if self.timestamp_column is not None:
            summary.update(self._timestamp_diagnostics(frame, warnings))
        return ProcessingResult(module_id=self.module_id, summary=summary, warnings=tuple(warnings))

    def _timestamp_diagnostics(self, frame: pd.DataFrame, warnings: list[str]) -> dict[str, int | bool]:
        if self.timestamp_column not in frame.columns:
            warnings.append(f"Timestamp column '{self.timestamp_column}' is missing.")
            return {"timestamp_ready": False, "duplicate_timestamps": 0}
        timestamps = pd.to_datetime(frame[self.timestamp_column], errors="coerce", utc=True)
        valid_timestamps = timestamps.dropna()
        duplicates = int(valid_timestamps.duplicated().sum())
        ordered = bool(valid_timestamps.is_monotonic_increasing)
        if len(valid_timestamps) != len(frame):
            warnings.append("Some timestamps are missing or could not be parsed.")
        if duplicates:
            warnings.append("Duplicate timestamps were detected.")
        if not ordered and len(valid_timestamps) > 1:
            warnings.append("Timestamps are not in ascending order.")
        return {
            "timestamp_ready": len(valid_timestamps) == len(frame) and duplicates == 0 and ordered,
            "duplicate_timestamps": duplicates,
            "timestamps_in_ascending_order": ordered,
        }
