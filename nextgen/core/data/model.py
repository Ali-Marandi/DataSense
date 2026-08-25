from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnProfile:
    """Privacy-safe summary of one column; it never retains sampled cell values."""

    name: str
    dtype: str
    missing: int
    unique: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.name,
            "dtype": self.dtype,
            "missing": self.missing,
            "unique": self.unique,
        }


@dataclass(frozen=True)
class DatasetProfile:
    """Immutable, aggregate-only profile used by UI and delivery services."""

    rows: int
    columns: int
    missing_cells: int
    duplicate_rows: int
    memory_mb: float
    column_summaries: tuple[ColumnProfile, ...]

    def __post_init__(self) -> None:
        numeric_fields = (self.rows, self.columns, self.missing_cells, self.duplicate_rows)
        if any(value < 0 for value in numeric_fields) or self.memory_mb < 0:
            raise ValueError("Dataset profile metrics cannot be negative.")
        if len(self.column_summaries) != self.columns:
            raise ValueError("Column profile count must equal the dataset column count.")

    def summary(self) -> dict[str, str]:
        return {
            "Rows": f"{self.rows:,}",
            "Columns": str(self.columns),
            "Missing cells": f"{self.missing_cells:,}",
            "Duplicate rows": f"{self.duplicate_rows:,}",
            "Memory": f"{self.memory_mb:.2f} MB",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "missing_cells": self.missing_cells,
            "duplicate_rows": self.duplicate_rows,
            "memory_mb": self.memory_mb,
            "column_summaries": [summary.to_dict() for summary in self.column_summaries],
        }

    def column(self, name: str) -> ColumnProfile:
        for summary in self.column_summaries:
            if summary.name == name:
                return summary
        raise KeyError(f"Column profile not found: {name}")
