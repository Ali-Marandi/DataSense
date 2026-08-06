"""Dataset loading, inspection and transformation with undo history."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

SUPPORTED_IMPORT = {
    ".csv": "Comma separated values",
    ".tsv": "Tab separated values",
    ".txt": "Delimited text",
    ".xls": "Excel workbook",
    ".xlsx": "Excel workbook",
    ".json": "JSON records",
    ".parquet": "Apache Parquet",
    ".db": "SQLite database",
    ".sqlite": "SQLite database",
}


@dataclass
class HistoryStep:
    label: str
    frame: pd.DataFrame


@dataclass
class DataManager:
    """Holds the active dataset and every mutation applied to it."""

    df: pd.DataFrame | None = None
    source: str | None = None
    history: list[HistoryStep] = field(default_factory=list)
    _redo: list[HistoryStep] = field(default_factory=list)

    # ---------------------------------------------------------------- loading
    def load(self, path: str, **options: Any) -> tuple[bool, str]:
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_IMPORT:
            return False, f"Unsupported file type: {ext or path}"
        try:
            if ext in (".csv", ".txt"):
                df = pd.read_csv(path, sep=options.get("sep", None), engine="python")
            elif ext == ".tsv":
                df = pd.read_csv(path, sep="\t")
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(path, sheet_name=options.get("sheet", 0))
            elif ext == ".json":
                df = pd.read_json(path)
            elif ext == ".parquet":
                df = pd.read_parquet(path)
            else:
                df = self._read_sqlite(path, options.get("table"))
        except Exception as exc:  # pragma: no cover - surfaced in the UI
            return False, str(exc)

        if isinstance(df, dict):
            df = next(iter(df.values()))
        self.df = df.reset_index(drop=True)
        self.source = path
        self.history = [HistoryStep("Imported dataset", self.df.copy())]
        self._redo.clear()
        return True, f"Loaded {len(self.df):,} rows x {self.df.shape[1]} columns"

    @staticmethod
    def _read_sqlite(path: str, table: str | None) -> pd.DataFrame:
        with sqlite3.connect(path) as conn:
            if not table:
                tables = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table'", conn
                )
                if tables.empty:
                    raise ValueError("This SQLite database contains no tables.")
                table = str(tables.iloc[0, 0])
            return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

    def set_frame(self, df: pd.DataFrame, label: str) -> None:
        """Record a new state so it can be undone later."""
        self.df = df.reset_index(drop=True)
        self.history.append(HistoryStep(label, self.df.copy()))
        self._redo.clear()

    # ---------------------------------------------------------------- history
    @property
    def can_undo(self) -> bool:
        return len(self.history) > 1

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> str | None:
        if not self.can_undo:
            return None
        step = self.history.pop()
        self._redo.append(step)
        self.df = self.history[-1].frame.copy()
        return step.label

    def redo(self) -> str | None:
        if not self._redo:
            return None
        step = self._redo.pop()
        self.history.append(step)
        self.df = step.frame.copy()
        return step.label

    # ------------------------------------------------------------ inspection
    @property
    def loaded(self) -> bool:
        return self.df is not None and not self.df.empty

    def columns(self) -> list[str]:
        return [] if self.df is None else list(self.df.columns)

    def numeric_columns(self) -> list[str]:
        if self.df is None:
            return []
        return list(self.df.select_dtypes(include=[np.number]).columns)

    def categorical_columns(self) -> list[str]:
        if self.df is None:
            return []
        return [c for c in self.df.columns if c not in self.numeric_columns()]

    def profile(self) -> pd.DataFrame:
        """Per-column quality profile used by the Data workspace."""
        if self.df is None:
            return pd.DataFrame()
        rows = []
        total = max(len(self.df), 1)
        for col in self.df.columns:
            s = self.df[col]
            missing = int(s.isna().sum())
            rows.append(
                {
                    "Column": col,
                    "Type": str(s.dtype),
                    "Non-null": int(s.notna().sum()),
                    "Missing": missing,
                    "Missing %": round(missing / total * 100, 2),
                    "Unique": int(s.nunique(dropna=True)),
                    "Mean": round(float(s.mean()), 4) if pd.api.types.is_numeric_dtype(s) else "",
                    "Std": round(float(s.std()), 4) if pd.api.types.is_numeric_dtype(s) else "",
                    "Min": s.min() if pd.api.types.is_numeric_dtype(s) else "",
                    "Max": s.max() if pd.api.types.is_numeric_dtype(s) else "",
                }
            )
        return pd.DataFrame(rows)

    def memory_usage_mb(self) -> float:
        if self.df is None:
            return 0.0
        return float(self.df.memory_usage(deep=True).sum()) / (1024 * 1024)

    # -------------------------------------------------------- transformations
    def drop_columns(self, columns: list[str]) -> None:
        self.set_frame(self.df.drop(columns=columns), f"Dropped {len(columns)} column(s)")

    def drop_missing(self, how: str = "any", subset: list[str] | None = None) -> int:
        before = len(self.df)
        self.set_frame(self.df.dropna(how=how, subset=subset or None), "Dropped missing rows")
        return before - len(self.df)

    def fill_missing(self, columns: list[str], strategy: str, value: str = "") -> None:
        df = self.df.copy()
        for col in columns:
            s = df[col]
            if strategy == "mean" and pd.api.types.is_numeric_dtype(s):
                df[col] = s.fillna(s.mean())
            elif strategy == "median" and pd.api.types.is_numeric_dtype(s):
                df[col] = s.fillna(s.median())
            elif strategy == "mode":
                mode = s.mode(dropna=True)
                if not mode.empty:
                    df[col] = s.fillna(mode.iloc[0])
            elif strategy == "forward":
                df[col] = s.ffill()
            elif strategy == "backward":
                df[col] = s.bfill()
            elif strategy == "constant":
                df[col] = s.fillna(value)
            elif strategy == "zero":
                df[col] = s.fillna(0)
        self.set_frame(df, f"Filled missing values ({strategy})")

    def drop_duplicates(self, subset: list[str] | None = None) -> int:
        before = len(self.df)
        self.set_frame(self.df.drop_duplicates(subset=subset or None), "Removed duplicates")
        return before - len(self.df)

    def rename_column(self, old: str, new: str) -> None:
        self.set_frame(self.df.rename(columns={old: new}), f"Renamed {old} to {new}")

    def cast_column(self, column: str, target: str) -> tuple[bool, str]:
        df = self.df.copy()
        try:
            if target == "numeric":
                df[column] = pd.to_numeric(df[column], errors="coerce")
            elif target == "datetime":
                df[column] = pd.to_datetime(df[column], errors="coerce")
            elif target == "category":
                df[column] = df[column].astype("category")
            else:
                df[column] = df[column].astype(str)
        except Exception as exc:
            return False, str(exc)
        self.set_frame(df, f"Converted {column} to {target}")
        return True, f"{column} converted to {target}"

    def scale_columns(self, columns: list[str], method: str = "standard") -> None:
        df = self.df.copy()
        for col in columns:
            s = pd.to_numeric(df[col], errors="coerce")
            if method == "standard":
                std = s.std() or 1.0
                df[col] = (s - s.mean()) / std
            else:
                span = (s.max() - s.min()) or 1.0
                df[col] = (s - s.min()) / span
        self.set_frame(df, f"Scaled {len(columns)} column(s) ({method})")

    def remove_outliers(self, columns: list[str], k: float = 1.5) -> int:
        df = self.df.copy()
        mask = pd.Series(True, index=df.index)
        for col in columns:
            s = pd.to_numeric(df[col], errors="coerce")
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            mask &= s.between(q1 - k * iqr, q3 + k * iqr) | s.isna()
        removed = int((~mask).sum())
        self.set_frame(df[mask], f"Removed {removed} outlier row(s)")
        return removed

    def query(self, expression: str) -> tuple[bool, str]:
        try:
            filtered = self.df.query(expression)
        except Exception as exc:
            return False, str(exc)
        self.set_frame(filtered, f"Filter: {expression}")
        return True, f"{len(filtered):,} rows match the filter"

    def add_computed_column(self, name: str, expression: str) -> tuple[bool, str]:
        try:
            values = self.df.eval(expression)
        except Exception as exc:
            return False, str(exc)
        df = self.df.copy()
        df[name] = values
        self.set_frame(df, f"Added column {name}")
        return True, f"Column {name} created"

    def group_aggregate(self, by: list[str], targets: list[str], funcs: list[str]) -> pd.DataFrame:
        grouped = self.df.groupby(by)[targets].agg(funcs)
        grouped.columns = ["_".join(map(str, c)) for c in grouped.columns.to_flat_index()]
        return grouped.reset_index()

    def pivot(self, index: str, columns: str, values: str, aggfunc: str) -> pd.DataFrame:
        table = pd.pivot_table(
            self.df, index=index, columns=columns, values=values, aggfunc=aggfunc
        )
        return table.reset_index()

    # ----------------------------------------------------------------- export
    def export(self, path: str) -> tuple[bool, str]:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                self.df.to_csv(path, index=False)
            elif ext == ".xlsx":
                self.df.to_excel(path, index=False)
            elif ext == ".json":
                self.df.to_json(path, orient="records", indent=2)
            elif ext == ".parquet":
                self.df.to_parquet(path, index=False)
            else:
                return False, f"Unsupported export format: {ext}"
        except Exception as exc:
            return False, str(exc)
        return True, f"Saved to {os.path.basename(path)}"
