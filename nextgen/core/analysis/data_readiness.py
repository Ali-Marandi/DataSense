from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.analysis.contracts import ProcessingContext, ProcessingResult


@dataclass(frozen=True)
class DataReadinessConfig:
    """Non-sensitive settings for local, descriptive data-readiness diagnostics."""

    iqr_multiplier: float = 1.5
    high_cardinality_ratio: float = 0.9
    minimum_numeric_observations: int = 4

    def __post_init__(self) -> None:
        if self.iqr_multiplier <= 0:
            raise ValueError("IQR multiplier must be greater than zero.")
        if not 0 < self.high_cardinality_ratio <= 1:
            raise ValueError("High-cardinality ratio must be in the interval (0, 1].")
        if self.minimum_numeric_observations < 4:
            raise ValueError("At least four numeric observations are required for IQR diagnostics.")


class DataReadinessInsightsModule:
    """Describe local dataset readiness without exposing cell values or making predictions.

    The module checks aggregate completeness, high-cardinality identifiers and robust
    IQR outliers. It is deliberately descriptive: it does not impute values, modify
    the DataFrame, create financial signals or send data outside the local process.
    """

    module_id = "data-readiness-insights/v1"

    def __init__(self, config: DataReadinessConfig | None = None) -> None:
        self.config = config or DataReadinessConfig()

    def process(self, frame: pd.DataFrame, context: ProcessingContext) -> ProcessingResult:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Data readiness diagnostics expects a pandas DataFrame.")
        if frame.empty:
            return ProcessingResult(
                module_id=self.module_id,
                summary={"ready": False, "rows": 0, "columns": int(len(frame.columns))},
                warnings=("The active dataset has no rows to analyze.",),
            )

        total_rows = len(frame)
        missing_columns = tuple(str(column) for column in frame.columns if int(frame[column].isna().sum()) > 0)
        high_cardinality = self._high_cardinality_columns(frame)
        numeric_insights = self._numeric_insights(frame)
        outlier_cells = sum(numeric_insights.values())
        warnings = self._warnings(missing_columns, high_cardinality, numeric_insights)
        readiness_score = self._readiness_score(
            total_rows=total_rows,
            missing_columns=missing_columns,
            high_cardinality=high_cardinality,
            outlier_cells=outlier_cells,
        )
        return ProcessingResult(
            module_id=self.module_id,
            summary={
                "ready": readiness_score >= 70,
                "rows": total_rows,
                "columns": int(len(frame.columns)),
                "numeric_columns": int(len(frame.select_dtypes(include="number").columns)),
                "columns_with_missing": int(len(missing_columns)),
                "high_cardinality_columns": int(len(high_cardinality)),
                "outlier_cells": int(outlier_cells),
                "readiness_score": int(readiness_score),
            },
            warnings=tuple(warnings),
        )

    def _high_cardinality_columns(self, frame: pd.DataFrame) -> tuple[str, ...]:
        flagged: list[str] = []
        for column in frame.columns:
            if pd.api.types.is_numeric_dtype(frame[column]):
                continue
            non_null = frame[column].dropna()
            if non_null.empty:
                continue
            ratio = non_null.nunique(dropna=True) / len(non_null)
            if ratio >= self.config.high_cardinality_ratio:
                flagged.append(str(column))
        return tuple(flagged)

    def _numeric_insights(self, frame: pd.DataFrame) -> dict[str, int]:
        findings: dict[str, int] = {}
        for column in frame.select_dtypes(include="number").columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if len(values) < self.config.minimum_numeric_observations:
                continue
            lower_quartile = values.quantile(0.25)
            upper_quartile = values.quantile(0.75)
            interquartile_range = upper_quartile - lower_quartile
            if interquartile_range == 0:
                continue
            lower_bound = lower_quartile - self.config.iqr_multiplier * interquartile_range
            upper_bound = upper_quartile + self.config.iqr_multiplier * interquartile_range
            count = int(((values < lower_bound) | (values > upper_bound)).sum())
            if count:
                findings[str(column)] = count
        return findings

    @staticmethod
    def _warnings(
        missing_columns: tuple[str, ...],
        high_cardinality: tuple[str, ...],
        numeric_insights: dict[str, int],
    ) -> list[str]:
        warnings: list[str] = []
        if missing_columns:
            warnings.append("Missing values detected in: " + ", ".join(missing_columns) + ".")
        if high_cardinality:
            warnings.append("High-cardinality columns may be identifiers: " + ", ".join(high_cardinality) + ".")
        if numeric_insights:
            summary = ", ".join(f"{column} ({count})" for column, count in sorted(numeric_insights.items()))
            warnings.append("IQR outlier observations detected in: " + summary + ".")
        return warnings

    @staticmethod
    def _readiness_score(
        *,
        total_rows: int,
        missing_columns: tuple[str, ...],
        high_cardinality: tuple[str, ...],
        outlier_cells: int,
    ) -> int:
        missing_penalty = min(40, len(missing_columns) * 10)
        identifier_penalty = min(20, len(high_cardinality) * 5)
        outlier_penalty = min(30, round((outlier_cells / max(total_rows, 1)) * 100))
        return max(0, 100 - missing_penalty - identifier_penalty - outlier_penalty)
