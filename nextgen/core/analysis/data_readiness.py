from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np
import pandas as pd

from core.analysis.contracts import ProcessingContext, ProcessingResult


@dataclass(frozen=True)
class DataReadinessConfig:
    """Validated, non-sensitive parameters for local data-readiness diagnostics."""

    iqr_multiplier: float = 1.5
    high_cardinality_ratio: float = 0.9
    minimum_numeric_observations: int = 4
    readiness_threshold: int = 70

    def __post_init__(self) -> None:
        if self.iqr_multiplier <= 0:
            raise ValueError("IQR multiplier must be greater than zero.")
        if not 0 < self.high_cardinality_ratio <= 1:
            raise ValueError("High-cardinality ratio must be in the interval (0, 1].")
        if self.minimum_numeric_observations < 4:
            raise ValueError("At least four numeric observations are required for IQR diagnostics.")
        if not 0 <= self.readiness_threshold <= 100:
            raise ValueError("Readiness threshold must be in the interval [0, 100].")


@dataclass(frozen=True)
class _NumericDiagnostics:
    outlier_cells_by_column: dict[str, int]
    non_finite_cells_by_column: dict[str, int]
    numeric_columns_considered: int
    finite_observations: int

    @property
    def outlier_cells(self) -> int:
        return sum(self.outlier_cells_by_column.values())

    @property
    def non_finite_cells(self) -> int:
        return sum(self.non_finite_cells_by_column.values())


class DataReadinessInsightsModule:
    """Describe local dataset readiness without exposing values or making predictions.

    The module is deterministic, does not mutate its DataFrame input and only emits
    aggregate counts plus column labels. It identifies missingness, likely identifier
    columns, non-finite numeric values and robust IQR outlier cells. It deliberately
    does not impute data, generate financial signals or send data outside the process.
    """

    module_id = "data-readiness-insights/v1"

    def __init__(self, config: DataReadinessConfig | None = None) -> None:
        self.config = config or DataReadinessConfig()

    def process(self, frame: pd.DataFrame, context: ProcessingContext) -> ProcessingResult:
        del context  # Contract compatibility; this local module has no context options yet.
        self._validate_frame(frame)
        if frame.empty:
            return ProcessingResult(
                module_id=self.module_id,
                summary={"ready": False, "rows": 0, "columns": int(len(frame.columns))},
                warnings=("The active dataset has no rows to analyze.",),
            )

        total_rows = len(frame)
        total_cells = max(total_rows * len(frame.columns), 1)
        missing_by_column = self._missing_cells_by_column(frame)
        high_cardinality = self._high_cardinality_columns(frame)
        numeric = self._numeric_diagnostics(frame)
        missing_cells = sum(missing_by_column.values())
        missing_ratio = missing_cells / total_cells
        outlier_ratio = numeric.outlier_cells / max(numeric.finite_observations, 1)
        readiness_score = self._readiness_score(
            missing_cell_ratio=missing_ratio,
            high_cardinality=high_cardinality,
            outlier_cell_ratio=outlier_ratio,
            non_finite_cells=numeric.non_finite_cells,
            total_rows=total_rows,
        )
        return ProcessingResult(
            module_id=self.module_id,
            summary={
                "ready": readiness_score >= self.config.readiness_threshold,
                "rows": total_rows,
                "columns": int(len(frame.columns)),
                "numeric_columns": int(len(frame.select_dtypes(include="number").columns)),
                "numeric_columns_considered": numeric.numeric_columns_considered,
                "finite_numeric_observations": numeric.finite_observations,
                "columns_with_missing": int(len(missing_by_column)),
                "missing_cells": int(missing_cells),
                "missing_cell_ratio": round(missing_ratio, 6),
                "high_cardinality_columns": int(len(high_cardinality)),
                "non_finite_numeric_cells": int(numeric.non_finite_cells),
                "outlier_cells": int(numeric.outlier_cells),
                "readiness_score": int(readiness_score),
            },
            warnings=tuple(
                self._warnings(
                    missing_by_column=missing_by_column,
                    high_cardinality=high_cardinality,
                    non_finite_cells_by_column=numeric.non_finite_cells_by_column,
                    outlier_cells_by_column=numeric.outlier_cells_by_column,
                )
            ),
        )

    @staticmethod
    def _validate_frame(frame: pd.DataFrame) -> None:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Data readiness diagnostics expects a pandas DataFrame.")
        if not frame.columns.is_unique:
            raise ValueError("Data readiness diagnostics requires unique column names.")

    @staticmethod
    def _missing_cells_by_column(frame: pd.DataFrame) -> dict[str, int]:
        counts = frame.isna().sum(axis=0)
        return {
            str(column): int(count)
            for column, count in counts.items()
            if int(count) > 0
        }

    def _high_cardinality_columns(self, frame: pd.DataFrame) -> tuple[str, ...]:
        non_numeric = frame.select_dtypes(exclude="number")
        flagged: list[str] = []
        for column in non_numeric.columns:
            values = non_numeric[column].dropna()
            if values.empty:
                continue
            ratio = values.nunique(dropna=True) / len(values)
            if ratio >= self.config.high_cardinality_ratio:
                flagged.append(str(column))
        return tuple(sorted(flagged))

    def _numeric_diagnostics(self, frame: pd.DataFrame) -> _NumericDiagnostics:
        outliers: dict[str, int] = {}
        non_finite: dict[str, int] = {}
        finite_observations = 0
        numeric_columns = frame.select_dtypes(include="number").columns
        considered = 0
        for column in numeric_columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if values.empty:
                continue
            values_as_float = values.to_numpy(dtype="float64", na_value=np.nan)
            finite_mask = np.isfinite(values_as_float)
            non_finite_count = int((~finite_mask).sum())
            column_name = str(column)
            if non_finite_count:
                non_finite[column_name] = non_finite_count
            finite_values = values[finite_mask]
            finite_observations += len(finite_values)
            if len(finite_values) < self.config.minimum_numeric_observations:
                continue
            considered += 1
            lower_quartile = finite_values.quantile(0.25)
            upper_quartile = finite_values.quantile(0.75)
            interquartile_range = upper_quartile - lower_quartile
            if not np.isfinite(interquartile_range) or interquartile_range == 0:
                continue
            lower_bound = lower_quartile - self.config.iqr_multiplier * interquartile_range
            upper_bound = upper_quartile + self.config.iqr_multiplier * interquartile_range
            count = int(((finite_values < lower_bound) | (finite_values > upper_bound)).sum())
            if count:
                outliers[column_name] = count
        return _NumericDiagnostics(
            outlier_cells_by_column=dict(sorted(outliers.items())),
            non_finite_cells_by_column=dict(sorted(non_finite.items())),
            numeric_columns_considered=considered,
            finite_observations=finite_observations,
        )

    @staticmethod
    def _warnings(
        *,
        missing_by_column: dict[str, int],
        high_cardinality: tuple[str, ...],
        non_finite_cells_by_column: dict[str, int],
        outlier_cells_by_column: dict[str, int],
    ) -> list[str]:
        warnings: list[str] = []
        if missing_by_column:
            warnings.append("Missing values detected in: " + ", ".join(sorted(missing_by_column)) + ".")
        if high_cardinality:
            warnings.append("High-cardinality columns may be identifiers: " + ", ".join(high_cardinality) + ".")
        if non_finite_cells_by_column:
            details = ", ".join(f"{column} ({count})" for column, count in non_finite_cells_by_column.items())
            warnings.append("Non-finite numeric values detected in: " + details + ".")
        if outlier_cells_by_column:
            details = ", ".join(f"{column} ({count})" for column, count in outlier_cells_by_column.items())
            warnings.append("IQR outlier observations detected in: " + details + ".")
        return warnings

    @staticmethod
    def _readiness_score(
        *,
        missing_cell_ratio: float,
        high_cardinality: tuple[str, ...],
        outlier_cell_ratio: float,
        non_finite_cells: int,
        total_rows: int,
    ) -> int:
        missing_penalty = min(40, ceil(missing_cell_ratio * 100))
        identifier_penalty = min(20, len(high_cardinality) * 5)
        outlier_penalty = min(30, ceil(outlier_cell_ratio * 100))
        non_finite_penalty = min(20, ceil((non_finite_cells / max(total_rows, 1)) * 100))
        return max(0, 100 - missing_penalty - identifier_penalty - outlier_penalty - non_finite_penalty)
