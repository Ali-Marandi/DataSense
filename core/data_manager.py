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
    ".avro": "Apache Avro",
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
    versions: dict[str, pd.DataFrame] = field(default_factory=dict)

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
            elif ext == ".avro":
                import pandavro as pdx
                df = pdx.read_avro(path)
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

    def get_data_preview(self, rows=10):
        """دریافت پیش‌نمایش داده‌ها"""
        if self.df is not None:
            return self.df.head(rows)
        return None

    def clean_data(self, fill_na=True, drop_duplicates=True):
        """پاکسازی هوشمند داده‌ها"""
        if self.df is None:
            return False, "داده‌ای برای پاکسازی وجود ندارد."
        
        try:
            if drop_duplicates:
                self.df.drop_duplicates(inplace=True)
            
            if fill_na:
                # پر کردن مقادیر خالی بر اساس نوع داده
                for col in self.df.columns:
                    if self.df[col].dtype in ['int64', 'float64']:
                        self.df[col] = self.df[col].fillna(self.df[col].mean())
                    else:
                        val = self.df[col].mode()[0] if not self.df[col].mode().empty else "Unknown"
                        self.df[col] = self.df[col].fillna(val)
            
            return True, "پاکسازی با موفقیت انجام شد."
        except Exception as e:
            return False, str(e)

    def save_version(self, version_name):
        """ذخیره نسخه فعلی داده‌ها"""
        if self.df is not None:
            self.versions[version_name] = self.df.copy()
            return True, f"نسخه '{version_name}' ذخیره شد."
        return False, "داده‌ای برای ذخیره وجود ندارد."

    def load_version(self, version_name):
        """بازیابی یک نسخه ذخیره شده"""
        if version_name in self.versions:
            self.df = self.versions[version_name].copy()
            self.history.append(HistoryStep(f"Restored version: {version_name}", self.df.copy()))
            return True, f"نسخه '{version_name}' بازیابی شد."
        return False, f"نسخه '{version_name}' یافت نشد."
