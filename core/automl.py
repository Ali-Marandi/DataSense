"""Deterministic AutoML orchestration over the supported DataSense ML engines."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from . import ml


@dataclass
class AutoMLResult:
    task: str
    target: str
    candidates: list[ml.ModelResult]
    best: ml.ModelResult


class AutoML:
    """Evaluate a bounded model family with fixed validation semantics and explicit winner selection."""

    def __init__(self, df: pd.DataFrame, *, time_column: str | None = None) -> None:
        self.df = df.copy()
        self.time_column = time_column
        self.result: AutoMLResult | None = None

    def _infer_task(self, target: str) -> str:
        series = self.df[target]
        if not pd.api.types.is_numeric_dtype(series) or series.nunique(dropna=True) <= 10:
            return "classification"
        return "regression"

    def run(self, target: str, features: list[str] | None = None, test_size: float = 0.2) -> AutoMLResult:
        if target not in self.df.columns:
            raise ValueError(f"Target column '{target}' is not present.")
        selected = [c for c in (features or self.df.columns.tolist()) if c != target and c in self.df.columns]
        if not selected:
            raise ValueError("At least one feature is required.")
        task = self._infer_task(target)
        candidates: list[ml.ModelResult] = []
        if task == "regression":
            names = ["Linear Regression", "Ridge Regression", "Random Forest", "Gradient Boosting"]
            for name in names:
                try:
                    candidates.append(ml.train_regression(self.df, target, selected, name, test_size, self.time_column))
                except ValueError:
                    continue
            if not candidates:
                raise ValueError("No regression model could be trained on the selected data.")
            best = max(candidates, key=lambda r: float(r.metrics["R2 (test)"]))
        else:
            names = ["Logistic Regression", "Decision Tree", "Random Forest", "Gradient Boosting"]
            for name in names:
                try:
                    candidates.append(ml.train_classification(self.df, target, selected, name, test_size, self.time_column))
                except ValueError:
                    continue
            if not candidates:
                raise ValueError("No classification model could be trained on the selected data.")
            best = max(candidates, key=lambda r: float(r.metrics["F1 (weighted)"]))
        self.result = AutoMLResult(task=task, target=target, candidates=candidates, best=best)
        return self.result

    def train_best_model(self, target_col: str):
        try:
            result = self.run(target_col)
            metric = "R2 (test)" if result.task == "regression" else "F1 (weighted)"
            return True, f"Best model: {result.best.title}; {metric}: {result.best.metrics[metric]:.4f}"
        except Exception as exc:
            return False, str(exc)

    def predict(self, input_data: pd.DataFrame):
        if self.result is None:
            return None, "Run AutoML before predicting."
        # AutoML returns reproducible evaluation metadata; persisted prediction should use
        # the normal model-store pathway rather than hiding a fitted estimator in this facade.
        estimator = self.result.best.metadata.get("fitted_estimator")
        if estimator is None:
            return None, "This AutoML result is evaluation-only; persist a selected model before scoring new data."
        try:
            return estimator.predict(input_data), None
        except Exception as exc:
            return None, str(exc)

    def summary(self) -> pd.DataFrame:
        if self.result is None:
            return pd.DataFrame()
        rows: list[dict[str, Any]] = []
        for candidate in self.result.candidates:
            row = {"model": candidate.title, **candidate.metrics}
            rows.append(row)
        return pd.DataFrame(rows)
