"""Automatic insight engine: profiles a dataset and ranks what matters."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

SEVERITY_WEIGHT = {"critical": 12.0, "warning": 5.0, "info": 0.0}


@dataclass
class Insight:
    title: str
    detail: str
    severity: str = "info"  # info | warning | critical
    category: str = "general"
    score: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


def _missing_insights(df: pd.DataFrame) -> list[Insight]:
    out: list[Insight] = []
    total = max(len(df), 1)
    for col in df.columns:
        ratio = float(df[col].isna().sum()) / total
        if ratio >= 0.4:
            out.append(Insight(
                f"'{col}' is mostly empty",
                f"{ratio * 100:.1f}% of values are missing; consider dropping or imputing the column.",
                "critical", "quality", ratio * 100,
            ))
        elif ratio >= 0.05:
            out.append(Insight(
                f"'{col}' has missing values",
                f"{ratio * 100:.1f}% of values are missing.",
                "warning", "quality", ratio * 100,
            ))
    return out


def _duplicate_insight(df: pd.DataFrame) -> list[Insight]:
    dupes = int(df.duplicated().sum())
    if not dupes:
        return []
    ratio = dupes / max(len(df), 1)
    return [Insight(
        "Duplicate rows detected",
        f"{dupes:,} duplicate row(s) ({ratio * 100:.1f}% of the dataset).",
        "critical" if ratio > 0.05 else "warning", "quality", ratio * 100,
    )]


def _constant_insights(df: pd.DataFrame) -> list[Insight]:
    out = []
    for col in df.columns:
        if df[col].nunique(dropna=True) <= 1:
            out.append(Insight(
                f"'{col}' carries no information",
                "Every row holds the same value; the column can be removed.",
                "warning", "quality", 20.0,
            ))
    return out


def _outlier_insights(df: pd.DataFrame) -> list[Insight]:
    out = []
    for col in df.select_dtypes(include=np.number).columns:
        series = df[col].dropna()
        if len(series) < 20:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        mask = (series < q1 - 3 * iqr) | (series > q3 + 3 * iqr)
        ratio = float(mask.sum()) / len(series)
        if ratio >= 0.01:
            out.append(Insight(
                f"Extreme outliers in '{col}'",
                f"{int(mask.sum()):,} value(s) ({ratio * 100:.1f}%) lie far outside the interquartile range.",
                "warning", "distribution", ratio * 100,
            ))
    return out


def _correlation_insights(df: pd.DataFrame, threshold: float = 0.75) -> list[Insight]:
    numeric = df.select_dtypes(include=np.number)
    if numeric.shape[1] < 2:
        return []
    corr = numeric.corr(numeric_only=True).abs()
    out = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            value = corr.loc[a, b]
            if pd.notna(value) and value >= threshold:
                out.append(Insight(
                    f"'{a}' and '{b}' move together",
                    f"Correlation of {value:.2f} — one of them may be redundant for modelling.",
                    "info", "relationship", float(value) * 40,
                ))
    return out


def _skew_insights(df: pd.DataFrame) -> list[Insight]:
    out = []
    for col in df.select_dtypes(include=np.number).columns:
        series = df[col].dropna()
        if len(series) < 30:
            continue
        skew = float(series.skew())
        if abs(skew) >= 2:
            out.append(Insight(
                f"'{col}' is heavily skewed",
                f"Skewness {skew:.2f}; a log or Box-Cox transform will stabilise models.",
                "info", "distribution", abs(skew) * 5,
            ))
    return out


def _imbalance_insights(df: pd.DataFrame) -> list[Insight]:
    out = []
    for col in df.columns:
        series = df[col].dropna()
        if pd.api.types.is_numeric_dtype(series) or series.empty:
            continue
        counts = series.value_counts(normalize=True)
        if len(counts) > 1 and counts.iloc[0] >= 0.9:
            out.append(Insight(
                f"'{col}' is highly imbalanced",
                f"'{counts.index[0]}' covers {counts.iloc[0] * 100:.1f}% of all rows.",
                "warning", "distribution", counts.iloc[0] * 30,
            ))
    return out


def generate_insights(df: pd.DataFrame, limit: int = 25) -> list[Insight]:
    """Return insights ordered by severity then impact score."""
    if df is None or df.empty:
        return []
    found: list[Insight] = []
    for fn in (
        _missing_insights, _duplicate_insight, _constant_insights,
        _outlier_insights, _correlation_insights, _skew_insights,
        _imbalance_insights,
    ):
        try:
            found.extend(fn(df))
        except Exception:  # pragma: no cover - defensive
            continue
    order = {"critical": 0, "warning": 1, "info": 2}
    found.sort(key=lambda i: (order.get(i.severity, 3), -i.score))
    return found[:limit]


def health_score(df: pd.DataFrame) -> float:
    """0-100 score describing how analysis-ready the dataset is."""
    if df is None or df.empty:
        return 0.0
    score = 100.0
    total_cells = df.size or 1
    score -= float(df.isna().sum().sum()) / total_cells * 40
    score -= float(df.duplicated().sum()) / max(len(df), 1) * 20
    constant = sum(1 for c in df.columns if df[c].nunique(dropna=True) <= 1)
    score -= constant / max(df.shape[1], 1) * 15
    for insight in generate_insights(df):
        if insight.severity == "critical":
            score -= 3
        elif insight.severity == "warning":
            score -= 1
    return float(max(0.0, min(100.0, round(score, 1))))


def insights_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = [i.as_dict() for i in generate_insights(df)]
    if not rows:
        return pd.DataFrame(columns=["severity", "category", "title", "detail"])
    frame = pd.DataFrame(rows)
    return frame[["severity", "category", "title", "detail"]]


def summary_metrics(df: pd.DataFrame) -> dict[str, str]:
    if df is None or df.empty:
        return {}
    return {
        "Rows": f"{len(df):,}",
        "Columns": str(df.shape[1]),
        "Missing cells": f"{int(df.isna().sum().sum()):,}",
        "Duplicate rows": f"{int(df.duplicated().sum()):,}",
        "Numeric columns": str(df.select_dtypes(include=np.number).shape[1]),
        "Health score": f"{health_score(df):.1f} / 100",
    }
