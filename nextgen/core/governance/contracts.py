from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

Severity = Literal["critical", "high", "medium", "low"]
RuleType = Literal["not_null", "unique"]
_VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low"})
_VALID_RULE_TYPES = frozenset({"not_null", "unique"})
_BLOCKING_SEVERITIES = frozenset({"critical", "high"})


@dataclass(frozen=True)
class DataQualityRule:
    rule_type: RuleType
    column: str
    severity: Severity = "high"

    def __post_init__(self) -> None:
        if self.rule_type not in _VALID_RULE_TYPES:
            raise ValueError(f"Unsupported rule type: {self.rule_type}")
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"Unsupported severity: {self.severity}")
        if not self.column.strip():
            raise ValueError("A data-quality rule requires a column name.")

    @property
    def key(self) -> tuple[str, str]:
        return self.rule_type, self.column


@dataclass(frozen=True)
class RuleResult:
    rule: DataQualityRule
    passed: bool
    violations: int
    detail: str

    def __post_init__(self) -> None:
        if self.violations < 0:
            raise ValueError("Violation count cannot be negative.")

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_type": self.rule.rule_type,
            "column": self.rule.column,
            "severity": self.rule.severity,
            "status": "pass" if self.passed else "fail",
            "violations": self.violations,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class QualityReport:
    results: tuple[RuleResult, ...]

    @property
    def failures(self) -> tuple[RuleResult, ...]:
        return tuple(result for result in self.results if not result.passed)

    @property
    def blocking_failures(self) -> tuple[RuleResult, ...]:
        return tuple(result for result in self.failures if result.rule.severity in _BLOCKING_SEVERITIES)

    @property
    def approved(self) -> bool:
        return not self.blocking_failures

    @property
    def total_violations(self) -> int:
        return sum(result.violations for result in self.results)

    def summary(self) -> dict[str, int | str]:
        return {
            "status": "approved" if self.approved else "blocked",
            "rules": len(self.results),
            "failed_rules": len(self.failures),
            "blocking_failures": len(self.blocking_failures),
            "total_violations": self.total_violations,
        }

    def to_rows(self) -> tuple[dict[str, object], ...]:
        return tuple(result.to_dict() for result in self.results)


@dataclass(frozen=True)
class DataContract:
    name: str
    rules: tuple[DataQualityRule, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("A data contract requires a name.")
        keys = [rule.key for rule in self.rules]
        if len(keys) != len(set(keys)):
            raise ValueError("A data contract cannot contain duplicate rules for the same column.")

    @classmethod
    def default(cls) -> "DataContract":
        return cls(
            name="Starter operations contract",
            rules=(
                DataQualityRule("not_null", "order_id", "critical"),
                DataQualityRule("unique", "order_id", "high"),
            ),
        )

    def evaluate(self, frame: pd.DataFrame) -> QualityReport:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("DataContract.evaluate expects a pandas DataFrame.")
        results: list[RuleResult] = []
        for rule in self.rules:
            results.append(self._evaluate_rule(rule, frame))
        return QualityReport(tuple(results))

    @staticmethod
    def _evaluate_rule(rule: DataQualityRule, frame: pd.DataFrame) -> RuleResult:
        if rule.column not in frame.columns:
            return RuleResult(rule, False, len(frame), "Required column is missing.")

        series = frame[rule.column]
        if rule.rule_type == "not_null":
            violations = int(series.isna().sum())
            detail = "All values are present." if violations == 0 else f"{violations} empty value(s)."
        elif rule.rule_type == "unique":
            # Nullability is governed by the separate not_null rule.  Unique only
            # considers supplied values, avoiding duplicate counting of missing cells.
            populated = series.dropna()
            violations = int(populated.duplicated(keep=False).sum())
            detail = "All populated values are unique." if violations == 0 else f"{violations} duplicate populated value(s)."
        else:  # __post_init__ prevents this; retain a defensive branch for extension safety.
            raise ValueError(f"Unsupported rule: {rule.rule_type}")
        return RuleResult(rule, violations == 0, violations, detail)
