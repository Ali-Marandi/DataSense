"""Dataset loading, inspection and transformation with undo/redo history.

v2.1: adds a high-performance loading path (chunked CSV reading, automatic
dtype downcasting, categorical compression) plus the full transformation API
used by the Prepare / Data / ML workspaces.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .lineage import LineageTrail
from .governance import (
    DataContract,
    QualityGatePolicy,
    QualityHistory,
    QualityReport,
    SchemaDriftPolicy,
    SchemaDriftReport,
    SchemaSnapshot,
    capture_schema,
    compare_schema,
)

SUPPORTED_IMPORT = {
    ".csv": "Comma separated values",
    ".tsv": "Tab separated values",
    ".txt": "Delimited text",
    ".xls": "Excel workbook",
    ".xlsx": "Excel workbook",
    ".json": "JSON records",
    ".parquet": "Apache Parquet",
    ".avro": "Apache Avro",
    ".db": "SQLite database",
    ".sqlite": "SQLite database",
}

# Files larger than this (bytes) are read in chunks to keep memory flat.
LARGE_FILE_THRESHOLD = 64 * 1024 * 1024
DEFAULT_CHUNK_ROWS = 250_000


def optimise_frame(df: pd.DataFrame, categorical_ratio: float = 0.5) -> pd.DataFrame:
    """Downcast numerics and convert low-cardinality objects to categories."""
    out = df.copy()
    for col in out.columns:
        series = out[col]
        if pd.api.types.is_integer_dtype(series):
            out[col] = pd.to_numeric(series, downcast="integer")
        elif pd.api.types.is_float_dtype(series):
            out[col] = pd.to_numeric(series, downcast="float")
        elif series.dtype == object or pd.api.types.is_string_dtype(series):
            non_null = series.dropna()
            if len(non_null) and non_null.nunique() / max(len(non_null), 1) < categorical_ratio:
                out[col] = series.astype("category")
    return out


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
    versions: dict[str, pd.DataFrame] = field(default_factory=dict)
    optimise_on_load: bool = True
    governance_contract: DataContract = field(default_factory=DataContract)
    governance_report: QualityReport | None = None
    quality_gate_policy: QualityGatePolicy = field(default_factory=QualityGatePolicy)
    quality_history: QualityHistory = field(default_factory=QualityHistory)
    schema_baseline: SchemaSnapshot | None = None
    schema_drift_policy: SchemaDriftPolicy = field(default_factory=SchemaDriftPolicy)
    lineage: LineageTrail = field(default_factory=LineageTrail)

    # ------------------------------------------------------------- properties
    @property
    def loaded(self) -> bool:
        return self.df is not None and not self.df.empty

    @property
    def columns(self) -> list[str]:
        return list(self.df.columns) if self.df is not None else []

    @property
    def numeric_columns(self) -> list[str]:
        if self.df is None:
            return []
        return [c for c in self.df.columns if pd.api.types.is_numeric_dtype(self.df[c])]

    @property
    def categorical_columns(self) -> list[str]:
        if self.df is None:
            return []
        return [
            c for c in self.df.columns
            if not pd.api.types.is_numeric_dtype(self.df[c])
            and not pd.api.types.is_datetime64_any_dtype(self.df[c])
        ]

    @property
    def datetime_columns(self) -> list[str]:
        if self.df is None:
            return []
        return [c for c in self.df.columns if pd.api.types.is_datetime64_any_dtype(self.df[c])]

    @property
    def can_undo(self) -> bool:
        return len(self.history) > 1

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def get_columns(self) -> list[str]:
        return self.columns

    def memory_usage_mb(self) -> float:
        if self.df is None:
            return 0.0
        return float(self.df.memory_usage(deep=True).sum()) / (1024 * 1024)

    # ---------------------------------------------------------------- loading
    def load(self, path: str, **options: Any) -> tuple[bool, str]:
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_IMPORT:
            return False, f"Unsupported file type: {ext or path}"
        try:
            if ext in (".csv", ".txt", ".tsv"):
                df = self._read_delimited(path, ext, options)
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(path, sheet_name=options.get("sheet", 0))
            elif ext == ".json":
                df = pd.read_json(path)
            elif ext == ".parquet":
                df = pd.read_parquet(path)
            elif ext == ".avro":
                import pandavro as pdx
                df = pdx.read_avro(path)
            else:
                df = self._read_sqlite(path, options.get("table"))
        except Exception as exc:  # pragma: no cover - surfaced in the UI
            return False, str(exc)

        if isinstance(df, dict):
            df = next(iter(df.values()))
        df = df.reset_index(drop=True)
        if self.optimise_on_load and options.get("optimise", True):
            df = optimise_frame(df)
        self.df = df
        self.source = path
        self.history = [HistoryStep("Imported dataset", self.df.copy())]
        self._redo.clear()
        self.governance_contract = DataContract()
        self.governance_report = None
        self.quality_gate_policy = QualityGatePolicy()
        self.quality_history = QualityHistory()
        self.schema_baseline = None
        self.schema_drift_policy = SchemaDriftPolicy()
        self.lineage = LineageTrail()
        self.lineage.record("Imported dataset", None, self.df, source=path)
        return True, f"Loaded {len(self.df):,} rows x {self.df.shape[1]} columns"

    def _read_delimited(self, path: str, ext: str, options: dict[str, Any]) -> pd.DataFrame:
        sep = options.get("sep") or ("\t" if ext == ".tsv" else None)
        big = os.path.getsize(path) > int(options.get("chunk_threshold", LARGE_FILE_THRESHOLD))
        if not big:
            return pd.read_csv(path, sep=sep, engine="python" if sep is None else "c")
        chunks: list[pd.DataFrame] = []
        reader = pd.read_csv(
            path,
            sep=sep or ",",
            chunksize=int(options.get("chunksize", DEFAULT_CHUNK_ROWS)),
            low_memory=True,
        )
        for chunk in reader:
            chunks.append(optimise_frame(chunk))
        return pd.concat(chunks, ignore_index=True)

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

    def export(self, path: str) -> tuple[bool, str]:
        if not self.loaded:
            return False, "No dataset to export."
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                self.df.to_csv(path, index=False)
            elif ext in (".xls", ".xlsx"):
                self.df.to_excel(path, index=False)
            elif ext == ".json":
                self.df.to_json(path, orient="records", indent=2)
            elif ext == ".parquet":
                self.df.to_parquet(path, index=False)
            else:
                return False, f"Unsupported export type: {ext}"
        except Exception as exc:
            return False, str(exc)
        return True, f"Exported {len(self.df):,} rows to {path}"

    # ------------------------------------------------------------ mutations
    def set_frame(self, frame: pd.DataFrame, label: str) -> None:
        before = self.df.copy() if self.df is not None else None
        self.df = frame.reset_index(drop=True)
        self.lineage.record(label, before, self.df, source=self.source)
        self.history.append(HistoryStep(label, self.df.copy()))
        self.history = self.history[-50:]
        self._redo.clear()
        # A previous validation report no longer describes the working dataset.
        self.governance_report = None

    def undo(self) -> str | None:
        if not self.can_undo:
            return None
        step = self.history.pop()
        before = self.df.copy() if self.df is not None else None
        self._redo.append(step)
        self.df = self.history[-1].frame.copy()
        self.lineage.record(f"Undo: {step.label}", before, self.df, source=self.source)
        return step.label

    def redo(self) -> str | None:
        if not self._redo:
            return None
        step = self._redo.pop()
        before = self.df.copy() if self.df is not None else None
        self.history.append(step)
        self.df = step.frame.copy()
        self.lineage.record(f"Redo: {step.label}", before, self.df, source=self.source)
        return step.label

    def _require(self) -> pd.DataFrame:
        if not self.loaded:
            raise ValueError("No dataset loaded.")
        return self.df

    def drop_columns(self, columns: Iterable[str]) -> tuple[bool, str]:
        try:
            df = self._require()
            cols = [c for c in columns if c in df.columns]
            if not cols:
                return False, "No matching columns."
            self.set_frame(df.drop(columns=cols), f"Dropped columns: {', '.join(cols)}")
            return True, f"Dropped {len(cols)} column(s)."
        except Exception as exc:
            return False, str(exc)

    def rename_column(self, old: str, new: str) -> tuple[bool, str]:
        try:
            df = self._require()
            if old not in df.columns:
                return False, f"Column '{old}' not found."
            self.set_frame(df.rename(columns={old: new}), f"Renamed {old} -> {new}")
            return True, f"Renamed '{old}' to '{new}'."
        except Exception as exc:
            return False, str(exc)

    def cast_column(self, column: str, dtype: str) -> tuple[bool, str]:
        try:
            df = self._require().copy()
            if dtype == "datetime":
                df[column] = pd.to_datetime(df[column], errors="coerce")
            elif dtype == "numeric":
                df[column] = pd.to_numeric(df[column], errors="coerce")
            elif dtype == "category":
                df[column] = df[column].astype("category")
            else:
                df[column] = df[column].astype(str)
            self.set_frame(df, f"Cast {column} to {dtype}")
            return True, f"'{column}' cast to {dtype}."
        except Exception as exc:
            return False, str(exc)

    def drop_duplicates(self, subset: list[str] | None = None) -> tuple[bool, str]:
        try:
            df = self._require()
            before = len(df)
            out = df.drop_duplicates(subset=subset or None)
            self.set_frame(out, "Dropped duplicate rows")
            return True, f"Removed {before - len(out):,} duplicate row(s)."
        except Exception as exc:
            return False, str(exc)

    def drop_missing(self, columns: list[str] | None = None, how: str = "any") -> tuple[bool, str]:
        try:
            df = self._require()
            before = len(df)
            out = df.dropna(subset=columns or None, how=how)
            self.set_frame(out, "Dropped rows with missing values")
            return True, f"Removed {before - len(out):,} row(s)."
        except Exception as exc:
            return False, str(exc)

    def fill_missing(self, column: str, strategy: str = "mean", value: Any = None) -> tuple[bool, str]:
        try:
            df = self._require().copy()
            series = df[column]
            if strategy == "mean" and pd.api.types.is_numeric_dtype(series):
                filler = series.mean()
            elif strategy == "median" and pd.api.types.is_numeric_dtype(series):
                filler = series.median()
            elif strategy == "mode":
                modes = series.mode()
                filler = modes.iloc[0] if not modes.empty else value
            elif strategy == "ffill":
                df[column] = series.ffill()
                self.set_frame(df, f"Forward filled {column}")
                return True, f"Forward filled '{column}'."
            elif strategy == "bfill":
                df[column] = series.bfill()
                self.set_frame(df, f"Back filled {column}")
                return True, f"Back filled '{column}'."
            else:
                filler = value
            df[column] = series.fillna(filler)
            self.set_frame(df, f"Filled missing values in {column}")
            return True, f"Filled missing values in '{column}'."
        except Exception as exc:
            return False, str(exc)

    def remove_outliers(self, column: str, method: str = "iqr", threshold: float = 1.5) -> tuple[bool, str]:
        try:
            df = self._require()
            series = pd.to_numeric(df[column], errors="coerce")
            if method == "zscore":
                std = series.std(ddof=0) or 1.0
                mask = ((series - series.mean()).abs() / std) <= threshold
            else:
                q1, q3 = series.quantile(0.25), series.quantile(0.75)
                iqr = q3 - q1
                mask = series.between(q1 - threshold * iqr, q3 + threshold * iqr)
            out = df[mask.fillna(False)]
            removed = len(df) - len(out)
            self.set_frame(out, f"Removed outliers in {column}")
            return True, f"Removed {removed:,} outlier row(s)."
        except Exception as exc:
            return False, str(exc)

    def scale_columns(self, columns: list[str], method: str = "standard") -> tuple[bool, str]:
        try:
            df = self._require().copy()
            for col in columns:
                series = pd.to_numeric(df[col], errors="coerce")
                if method == "minmax":
                    rng = series.max() - series.min()
                    df[col] = (series - series.min()) / (rng if rng else 1)
                elif method == "robust":
                    iqr = series.quantile(0.75) - series.quantile(0.25)
                    df[col] = (series - series.median()) / (iqr if iqr else 1)
                else:
                    std = series.std(ddof=0)
                    df[col] = (series - series.mean()) / (std if std else 1)
            self.set_frame(df, f"Scaled columns ({method})")
            return True, f"Scaled {len(columns)} column(s)."
        except Exception as exc:
            return False, str(exc)

    def add_computed_column(self, name: str, expression: str) -> tuple[bool, str]:
        try:
            df = self._require().copy()
            df[name] = df.eval(expression)
            self.set_frame(df, f"Added computed column {name}")
            return True, f"Added column '{name}'."
        except Exception as exc:
            return False, str(exc)

    def group_aggregate(self, by: list[str], column: str, func: str = "mean") -> tuple[bool, str]:
        try:
            df = self._require()
            out = df.groupby(by, dropna=False)[column].agg(func).reset_index()
            self.set_frame(out, f"Grouped by {', '.join(by)} ({func} of {column})")
            return True, f"Aggregated into {len(out):,} group(s)."
        except Exception as exc:
            return False, str(exc)

    def pivot(self, index: str, columns: str, values: str, aggfunc: str = "mean") -> tuple[bool, str]:
        try:
            df = self._require()
            out = pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=aggfunc)
            out = out.reset_index()
            out.columns = [str(c) for c in out.columns]
            self.set_frame(out, f"Pivoted {values} by {index}/{columns}")
            return True, f"Pivot table with {len(out):,} row(s)."
        except Exception as exc:
            return False, str(exc)

    def query(self, expression: str) -> tuple[bool, str]:
        try:
            df = self._require()
            out = df.query(expression)
            self.set_frame(out, f"Filtered: {expression}")
            return True, f"{len(out):,} row(s) match."
        except Exception as exc:
            return False, str(exc)

    # ---------------------------------------------------------------- profile
    def profile(self) -> pd.DataFrame:
        if not self.loaded:
            return pd.DataFrame()
        df = self.df
        rows = []
        for col in df.columns:
            series = df[col]
            missing = int(series.isna().sum())
            row: dict[str, Any] = {
                "column": col,
                "dtype": str(series.dtype),
                "missing": missing,
                "missing %": round(missing / max(len(df), 1) * 100, 2),
                "unique": int(series.nunique(dropna=True)),
            }
            if pd.api.types.is_numeric_dtype(series):
                row.update(
                    {
                        "mean": round(float(series.mean()), 4) if len(series.dropna()) else np.nan,
                        "std": round(float(series.std()), 4) if len(series.dropna()) > 1 else np.nan,
                        "min": series.min(),
                        "max": series.max(),
                    }
                )
            rows.append(row)
        return pd.DataFrame(rows)

    def get_summary(self) -> str:
        if not self.loaded:
            return "No dataset loaded."
        df = self.df
        return (
            f"{len(df):,} rows x {df.shape[1]} columns, "
            f"{int(df.isna().sum().sum()):,} missing cells, "
            f"{self.memory_usage_mb():.2f} MB in memory."
        )

    def get_data_preview(self, rows: int = 10):
        return self.df.head(rows) if self.df is not None else None

    def optimise_memory(self) -> tuple[bool, str]:
        if not self.loaded:
            return False, "No dataset loaded."
        before = self.memory_usage_mb()
        self.set_frame(optimise_frame(self.df), "Optimised memory usage")
        after = self.memory_usage_mb()
        saved = max(before - after, 0.0)
        return True, f"Memory {before:.2f} MB -> {after:.2f} MB (saved {saved:.2f} MB)."

    def clean_data(self, fill_na: bool = True, drop_duplicates: bool = True) -> tuple[bool, str]:
        if not self.loaded:
            return False, "No dataset to clean."
        try:
            df = self.df.copy()
            if drop_duplicates:
                df = df.drop_duplicates()
            if fill_na:
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].mean())
                    else:
                        modes = df[col].mode()
                        df[col] = df[col].fillna(modes.iloc[0] if not modes.empty else "Unknown")
            self.set_frame(df, "Smart cleaning applied")
            return True, "Cleaning completed successfully."
        except Exception as exc:
            return False, str(exc)

    # -------------------------------------------------------------- governance
    def set_governance_contract(self, contract: DataContract) -> None:
        self.governance_contract = contract
        self.governance_report = None

    def set_quality_gate_policy(self, policy: QualityGatePolicy) -> None:
        self.quality_gate_policy = policy

    def set_schema_baseline(self) -> SchemaSnapshot:
        baseline = capture_schema(self._require())
        if baseline is None:  # defensive guard; _require already guarantees a frame
            raise ValueError("No dataset loaded.")
        self.schema_baseline = baseline
        return baseline

    def set_schema_drift_policy(self, policy: SchemaDriftPolicy) -> None:
        self.schema_drift_policy = policy

    def check_schema_drift(self) -> SchemaDriftReport:
        return compare_schema(self.schema_baseline, self.df, self.schema_drift_policy)

    def run_governance_checks(self) -> QualityReport:
        self.governance_report = self.governance_contract.execute(self.df)
        self.quality_history.add(self.governance_report, self.governance_report.gate_decision(self.quality_gate_policy))
        return self.governance_report

    # --------------------------------------------------------------- versions
    def save_version(self, version_name: str) -> tuple[bool, str]:
        if self.df is not None:
            self.versions[version_name] = self.df.copy()
            return True, f"Version '{version_name}' saved."
        return False, "No dataset to save."

    def load_version(self, version_name: str) -> tuple[bool, str]:
        if version_name in self.versions:
            self.set_frame(self.versions[version_name].copy(), f"Restored version: {version_name}")
            return True, f"Version '{version_name}' restored."
        return False, f"Version '{version_name}' not found."
