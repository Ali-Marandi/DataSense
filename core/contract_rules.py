"""Cross-column and dataset-level validation rules for DataSense governance."""
from __future__ import annotations

from typing import Any

import pandas as pd


def required_columns(rule_type: str, rule_column: str, params: dict[str, Any]) -> list[str]:
    """Return all columns required by a cross-column rule."""
    kind = rule_type.lower().strip()
    if kind in {"less_than_or_equal", "greater_than_or_equal", "equal"}:
        other = params.get("other_column")
        return [rule_column, str(other)] if other else [rule_column]
    if kind == "conditional_required":
        when_column = params.get("when_column")
        return [rule_column, str(when_column)] if when_column else [rule_column]
    if kind == "date_order":
        start = params.get("start_column", rule_column)
        end = params.get("end_column", params.get("other_column"))
        return [str(start), str(end)] if end else [str(start)]
    if kind == "sum_to":
        columns = params.get("columns", [])
        return [str(column) for column in columns] if isinstance(columns, list) else []
    if kind == "unique_combination":
        columns = params.get("columns", [])
        return [str(column) for column in columns] if isinstance(columns, list) else []
    return [rule_column]


def evaluate_cross_column(frame: pd.DataFrame, rule: Any, result_factory) -> Any | None:
    """Evaluate a cross-column/dataset rule, returning a QualityCheckResult or None."""
    kind = rule.rule_type.lower().strip()
    if kind not in {
        "less_than_or_equal", "greater_than_or_equal", "equal",
        "conditional_required", "date_order", "sum_to", "unique_combination",
    }:
        return None

    params = rule.params or {}
    columns = required_columns(kind, rule.column, params)
    missing = [column for column in columns if column not in frame.columns or not column]
    if missing:
        return result_factory(rule, "error", "Required column(s) missing", "All referenced columns must exist", detail="Missing: " + ", ".join(missing))

    if kind in {"less_than_or_equal", "greater_than_or_equal", "equal"}:
        other = columns[1]
        left = frame[rule.column]
        right = frame[other]
        operator = {"less_than_or_equal": lambda a, b: a <= b, "greater_than_or_equal": lambda a, b: a >= b, "equal": lambda a, b: (a - b).abs() <= float(params.get("tolerance", 0.0))}[kind]
        try:
            if kind == "equal":
                tolerance = float(params.get("tolerance", 0.0))
                if tolerance < 0:
                    raise ValueError("tolerance must be non-negative")
                bad = left.notna() & right.notna() & ~operator(pd.to_numeric(left, errors="coerce"), pd.to_numeric(right, errors="coerce"))
            else:
                bad = left.notna() & right.notna() & ~operator(left, right)
        except (TypeError, ValueError):
            return result_factory(rule, "error", "Invalid comparison values", "Comparable column values", detail="Referenced columns could not be compared safely.")
        violations = int(bad.fillna(False).sum())
        symbol = {"less_than_or_equal": "<=", "greater_than_or_equal": ">=", "equal": "="}[kind]
        return result_factory(rule, "pass" if violations == 0 else "fail", f"{violations:,} row(s) violate {rule.column} {symbol} {other}", f"Every non-null row satisfies {rule.column} {symbol} {other}", violations)

    if kind == "conditional_required":
        when_column = columns[1]
        trigger_values = params.get("when_values")
        if trigger_values is None and "when_value" in params:
            trigger_values = [params["when_value"]]
        if not isinstance(trigger_values, list) or not trigger_values:
            return result_factory(rule, "error", "No trigger values", "when_values must contain at least one value", detail="Configure when_values or when_value.")
        triggered = frame[when_column].isin(trigger_values)
        bad = triggered & frame[rule.column].isna()
        violations = int(bad.sum())
        return result_factory(rule, "pass" if violations == 0 else "fail", f"{violations:,} triggered row(s) missing {rule.column}", f"{rule.column} is required when {when_column} matches configured trigger values", violations)

    if kind == "date_order":
        start_column, end_column = columns
        start = pd.to_datetime(frame[start_column], errors="coerce", utc=True)
        end = pd.to_datetime(frame[end_column], errors="coerce", utc=True)
        allow_equal = bool(params.get("allow_equal", True))
        bad = start.notna() & end.notna() & (start > end if allow_equal else start >= end)
        violations = int(bad.sum())
        relation = "<=" if allow_equal else "<"
        return result_factory(rule, "pass" if violations == 0 else "fail", f"{violations:,} row(s) violate date order", f"{start_column} {relation} {end_column}", violations)

    if kind == "sum_to":
        target = params.get("target")
        if target is None:
            return result_factory(rule, "error", "No target", "Numeric target is required", detail="Configure params.target.")
        tolerance = float(params.get("tolerance", 0.0))
        if tolerance < 0:
            return result_factory(rule, "error", "Invalid tolerance", "Non-negative tolerance", detail="Configure a non-negative tolerance.")
        numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
        sums = numeric.sum(axis=1, min_count=len(columns))
        bad = sums.notna() & ((sums - float(target)).abs() > tolerance)
        violations = int(bad.sum())
        return result_factory(rule, "pass" if violations == 0 else "fail", f"{violations:,} row(s) do not sum to target", f"Sum({', '.join(columns)}) = {float(target):g} ± {tolerance:g}", violations)

    if kind == "unique_combination":
        if len(columns) < 2:
            return result_factory(rule, "error", "Insufficient columns", "At least two columns are required", detail="Configure params.columns with two or more columns.")
        duplicates = frame[columns].duplicated(keep="first")
        complete = frame[columns].notna().all(axis=1)
        bad = duplicates & complete
        violations = int(bad.sum())
        return result_factory(rule, "pass" if violations == 0 else "fail", f"{violations:,} duplicate combination(s)", f"Unique combinations of: {', '.join(columns)}", violations)

    return None
