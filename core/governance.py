"""Deterministic data-governance primitives for DataSense Trust Center.

The module is intentionally UI-independent: a saved project, a future scheduler, or a
command-line integration can run exactly the same contract without sending data away.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


PII_HINTS: dict[str, tuple[str, str]] = {
    "email": ("Email address", "Restricted"),
    "e-mail": ("Email address", "Restricted"),
    "phone": ("Phone number", "Restricted"),
    "mobile": ("Phone number", "Restricted"),
    "telephone": ("Phone number", "Restricted"),
    "ssn": ("Government identifier", "Restricted"),
    "national_id": ("Government identifier", "Restricted"),
    "passport": ("Government identifier", "Restricted"),
    "credit_card": ("Payment card", "Restricted"),
    "card_number": ("Payment card", "Restricted"),
    "iban": ("Financial account", "Restricted"),
    "address": ("Postal address", "Confidential"),
    "date_of_birth": ("Date of birth", "Confidential"),
    "birthdate": ("Date of birth", "Confidential"),
    "ip_address": ("IP address", "Confidential"),
    "ip": ("IP address", "Confidential"),
    "name": ("Personal name", "Confidential"),
}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
IP_RE = re.compile(r"^(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9().\-\s]{6,}[0-9]$")
CARD_RE = re.compile(r"^[0-9\s-]{13,25}$")


@dataclass(frozen=True)
class DataClassification:
    """A conservative sensitive-data finding. No observed values are retained."""

    column: str
    label: str
    sensitivity: str
    confidence: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class DataQualityRule:
    """A serialisable quality assertion applied to a single DataFrame column."""

    rule_type: str
    column: str
    params: dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"
    name: str = ""

    def display_name(self) -> str:
        return self.name or f"{self.column}: {self.rule_type.replace('_', ' ')}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DataQualityRule":
        return cls(
            rule_type=str(value.get("rule_type", "")),
            column=str(value.get("column", "")),
            params=dict(value.get("params", {}) or {}),
            severity=str(value.get("severity", "medium")),
            name=str(value.get("name", "")),
        )


@dataclass(frozen=True)
class QualityCheckResult:
    """A single contract assertion result with privacy-preserving diagnostics."""

    rule: DataQualityRule
    status: str
    observed: str
    expected: str
    violations: int = 0
    detail: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.to_dict(),
            "status": self.status,
            "observed": self.observed,
            "expected": self.expected,
            "violations": self.violations,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class QualityGatePolicy:
    """A serialisable release gate that turns quality evidence into a deterministic decision."""

    name: str = "Default production gate"
    minimum_score: float = 95.0
    maximum_critical_failures: int = 0
    maximum_high_failures: int = 0
    block_on_error: bool = True

    def __post_init__(self) -> None:
        if not 0 <= float(self.minimum_score) <= 100:
            raise ValueError("minimum_score must be between 0 and 100")
        if self.maximum_critical_failures < 0 or self.maximum_high_failures < 0:
            raise ValueError("maximum failures cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "QualityGatePolicy":
        if not value:
            return cls()
        return cls(
            name=str(value.get("name", "Default production gate")),
            minimum_score=float(value.get("minimum_score", 95.0)),
            maximum_critical_failures=int(value.get("maximum_critical_failures", 0)),
            maximum_high_failures=int(value.get("maximum_high_failures", 0)),
            block_on_error=bool(value.get("block_on_error", True)),
        )


@dataclass(frozen=True)
class QualityGateDecision:
    policy_name: str
    decision: str
    reasons: tuple[str, ...]
    score: float | None

    @property
    def allowed(self) -> bool:
        return self.decision == "approved"

    def to_dict(self) -> dict[str, Any]:
        return {"policy_name": self.policy_name, "decision": self.decision, "reasons": list(self.reasons), "score": self.score}


@dataclass(frozen=True)
class QualityRunRecord:
    """Privacy-preserving historical evidence; it retains outcomes and no dataset values."""

    contract_name: str
    generated_at: str
    rows: int
    score: float | None
    status: str
    gate_decision: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QualityRunRecord":
        score = value.get("score")
        return cls(
            contract_name=str(value.get("contract_name", "")),
            generated_at=str(value.get("generated_at", "")),
            rows=int(value.get("rows", 0)),
            score=None if score is None else float(score),
            status=str(value.get("status", "not configured")),
            gate_decision=str(value.get("gate_decision", "not configured")),
        )


@dataclass
class QualityHistory:
    """Bounded quality trend suitable for .dsproj persistence and executive reporting."""

    records: list[QualityRunRecord] = field(default_factory=list)
    max_records: int = 90

    def add(self, report: "QualityReport", decision: QualityGateDecision) -> QualityRunRecord:
        record = QualityRunRecord(report.contract_name, report.generated_at, report.rows, report.score, report.status, decision.decision)
        self.records.append(record)
        self.records = self.records[-max(int(self.max_records), 1):]
        return record

    def trend(self) -> str:
        values = [record.score for record in self.records if record.score is not None]
        if len(values) < 2:
            return "insufficient data"
        delta = values[-1] - values[-2]
        if delta >= 1.0:
            return "improving"
        if delta <= -1.0:
            return "declining"
        return "stable"

    def to_dict(self) -> dict[str, Any]:
        return {"max_records": self.max_records, "trend": self.trend(), "records": [record.to_dict() for record in self.records]}

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "QualityHistory":
        if not value:
            return cls()
        return cls(
            max_records=max(int(value.get("max_records", 90)), 1),
            records=[QualityRunRecord.from_dict(item) for item in value.get("records", [])],
        )


@dataclass
class QualityReport:
    """The immutable-at-export evidence produced by one contract execution."""

    contract_name: str
    rows: int
    results: list[QualityCheckResult] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )

    @property
    def evaluated(self) -> list[QualityCheckResult]:
        return [result for result in self.results if result.status in {"pass", "fail", "error"}]

    @property
    def score(self) -> float | None:
        """Weighted pass-rate; no configured/evaluated rules intentionally has no score."""
        if not self.evaluated:
            return None
        weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        total = sum(weights.get(result.rule.severity.lower(), 2) for result in self.evaluated)
        passed = sum(
            weights.get(result.rule.severity.lower(), 2)
            for result in self.evaluated
            if result.status == "pass"
        )
        return round(100 * passed / max(total, 1), 1)

    @property
    def status(self) -> str:
        if not self.evaluated:
            return "not configured"
        if any(result.status == "error" for result in self.evaluated):
            return "needs attention"
        if any(result.status == "fail" and result.rule.severity.lower() == "critical" for result in self.evaluated):
            return "blocked"
        if any(result.status == "fail" for result in self.evaluated):
            return "needs attention"
        return "trusted"

    def gate_decision(self, policy: QualityGatePolicy | None = None) -> QualityGateDecision:
        """Apply a policy after execution without changing the independently computed quality score."""
        policy = policy or QualityGatePolicy()
        if self.score is None:
            return QualityGateDecision(policy.name, "not configured", ("No evaluated quality rules are available.",), self.score)
        errors = sum(result.status == "error" for result in self.evaluated)
        critical = sum(result.status == "fail" and result.rule.severity.lower() == "critical" for result in self.evaluated)
        high = sum(result.status == "fail" and result.rule.severity.lower() == "high" for result in self.evaluated)
        reasons: list[str] = []
        if policy.block_on_error and errors:
            reasons.append(f"{errors} rule execution error(s) require review.")
        if critical > policy.maximum_critical_failures:
            reasons.append(f"{critical} critical failure(s) exceed the limit of {policy.maximum_critical_failures}.")
        if high > policy.maximum_high_failures:
            reasons.append(f"{high} high-severity failure(s) exceed the limit of {policy.maximum_high_failures}.")
        if self.score < policy.minimum_score:
            reasons.append(f"Score {self.score:.1f}% is below the minimum {policy.minimum_score:.1f}%.")
        return QualityGateDecision(policy.name, "blocked" if reasons else "approved", tuple(reasons or ("All configured quality gate conditions passed.",)), self.score)

    def summary(self) -> dict[str, Any]:
        return {
            "Contract": self.contract_name,
            "Rows": self.rows,
            "Rules": len(self.results),
            "Passed": sum(result.status == "pass" for result in self.results),
            "Failed": sum(result.status == "fail" for result in self.results),
            "Errors": sum(result.status == "error" for result in self.results),
            "Score": "Not configured" if self.score is None else f"{self.score:.1f}%",
            "Status": self.status.title(),
            "Generated (UTC)": self.generated_at,
        }

    def to_frame(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for result in self.results:
            rows.append(
                {
                    "status": result.status,
                    "severity": result.rule.severity,
                    "rule": result.rule.display_name(),
                    "column": result.rule.column,
                    "observed": result.observed,
                    "expected": result.expected,
                    "violations": result.violations,
                    "detail": result.detail,
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "status",
                "severity",
                "rule",
                "column",
                "observed",
                "expected",
                "violations",
                "detail",
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "rows": self.rows,
            "generated_at": self.generated_at,
            "status": self.status,
            "score": self.score,
            "summary": self.summary(),
            "gate_decision": self.gate_decision().to_dict(),
            "results": [result.to_dict() for result in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)


@dataclass
class DataContract:
    """A named, portable collection of deterministic data-quality rules."""

    name: str = "DataSense data contract"
    rules: list[DataQualityRule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "rules": [rule.to_dict() for rule in self.rules]}

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "DataContract":
        if not value:
            return cls()
        return cls(
            name=str(value.get("name", "DataSense data contract")),
            rules=[DataQualityRule.from_dict(rule) for rule in value.get("rules", [])],
        )

    def execute(self, frame: pd.DataFrame | None) -> QualityReport:
        if frame is None:
            return QualityReport(contract_name=self.name, rows=0)
        return QualityReport(
            contract_name=self.name,
            rows=len(frame),
            results=[evaluate_rule(frame, rule) for rule in self.rules],
        )


def _result(
    rule: DataQualityRule,
    status: str,
    observed: str,
    expected: str,
    violations: int = 0,
    detail: str = "",
) -> QualityCheckResult:
    return QualityCheckResult(rule, status, observed, expected, int(violations), detail)


def evaluate_rule(frame: pd.DataFrame, rule: DataQualityRule) -> QualityCheckResult:
    """Run one rule. Unexpected invalid configuration becomes an explicit audit error."""
    if rule.column not in frame.columns:
        return _result(rule, "error", "Column missing", "Column must exist", detail="The selected column is absent.")

    series = frame[rule.column]
    kind = rule.rule_type.lower().strip()
    try:
        if kind == "not_null":
            violations = int(series.isna().sum())
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"{violations:,} null value(s)",
                "0 null values",
                violations,
            )

        if kind == "unique":
            present = series.dropna()
            violations = int(present.duplicated().sum())
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"{violations:,} duplicate value(s)",
                "All non-null values unique",
                violations,
            )

        if kind == "range":
            numeric = pd.to_numeric(series, errors="coerce")
            lower = rule.params.get("min")
            upper = rule.params.get("max")
            if lower is None and upper is None:
                return _result(rule, "error", "No bounds", "At least one bound", detail="Configure min and/or max.")
            bad = pd.Series(False, index=series.index)
            limits: list[str] = []
            if lower is not None:
                lower_value = float(lower)
                bad |= numeric < lower_value
                limits.append(f">= {lower_value:g}")
            if upper is not None:
                upper_value = float(upper)
                bad |= numeric > upper_value
                limits.append(f"<= {upper_value:g}")
            violations = int(bad.fillna(False).sum())
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"{violations:,} value(s) outside bounds",
                " and ".join(limits),
                violations,
            )

        if kind == "allowed_values":
            values = rule.params.get("values", [])
            if not isinstance(values, list) or not values:
                return _result(rule, "error", "No allowed values", "One or more allowed values", detail="Configure allowed values.")
            bad = series.notna() & ~series.isin(values)
            violations = int(bad.sum())
            visible = ", ".join(str(value) for value in values[:8])
            expected = f"One of: {visible}{' …' if len(values) > 8 else ''}"
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"{violations:,} unexpected value(s)",
                expected,
                violations,
            )

        if kind == "regex":
            pattern = str(rule.params.get("pattern", ""))
            if not pattern:
                return _result(rule, "error", "No pattern", "Valid regular expression", detail="Configure a regex pattern.")
            valid = series.dropna().astype(str).str.fullmatch(pattern, na=False)
            violations = int((~valid).sum())
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"{violations:,} non-matching value(s)",
                f"Matches /{pattern}/",
                violations,
            )

        if kind == "freshness":
            max_age_days = float(rule.params.get("max_age_days", 0))
            if max_age_days <= 0:
                return _result(rule, "error", "Invalid age", "Positive max_age_days", detail="Configure a positive age.")
            dates = pd.to_datetime(series, errors="coerce", utc=True).dropna()
            if dates.empty:
                return _result(rule, "error", "No parseable timestamp", "Recent timestamp", detail="No valid dates found.")
            newest = dates.max()
            now = pd.Timestamp.now(tz="UTC")
            age = max((now - newest).total_seconds() / 86400, 0.0)
            violations = 0 if age <= max_age_days else 1
            return _result(
                rule,
                "pass" if violations == 0 else "fail",
                f"Newest value is {age:.1f} day(s) old",
                f"Newest value <= {max_age_days:g} day(s) old",
                violations,
            )

        return _result(rule, "error", f"Unknown rule: {rule.rule_type}", "Supported rule type", detail="Unsupported rule type.")
    except (TypeError, ValueError, re.error) as exc:
        return _result(rule, "error", "Invalid rule configuration", "Valid rule parameters", detail=str(exc))


def recommended_rules(frame: pd.DataFrame | None) -> list[DataQualityRule]:
    """Create conservative, reviewable starter rules; no rule changes data."""
    if frame is None or frame.empty:
        return []
    rules: list[DataQualityRule] = []
    for column in frame.columns:
        series = frame[column]
        normalized = str(column).lower().replace(" ", "_")
        non_null = int(series.notna().sum())
        nulls = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        identifier = any(token in normalized for token in ("_id", "id_", "key", "code", "email"))

        if non_null and (nulls == 0 or identifier):
            rules.append(
                DataQualityRule(
                    "not_null",
                    str(column),
                    severity="high" if identifier else "medium",
                    name=f"{column} must be populated",
                )
            )
        if identifier and non_null and unique == non_null:
            rules.append(
                DataQualityRule(
                    "unique",
                    str(column),
                    severity="high",
                    name=f"{column} must be unique",
                )
            )
        if 1 < unique <= 12 and non_null and non_null / max(len(frame), 1) >= 0.95:
            values = [value.item() if hasattr(value, "item") else value for value in series.dropna().unique().tolist()]
            rules.append(
                DataQualityRule(
                    "allowed_values",
                    str(column),
                    params={"values": values},
                    severity="low",
                    name=f"{column} accepted values",
                )
            )
    return rules


def _luhn_valid(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _match_ratio(values: pd.Series, matcher) -> float:
    if values.empty:
        return 0.0
    return sum(bool(matcher(str(value).strip())) for value in values) / len(values)


def scan_sensitive_data(frame: pd.DataFrame | None, sample_size: int = 250) -> list[DataClassification]:
    """Identify likely PII without exporting, logging, or retaining value samples."""
    if frame is None or frame.empty:
        return []
    findings: list[DataClassification] = []
    for column in frame.columns:
        name = str(column)
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        values = frame[column].dropna().astype(str).head(sample_size)
        hint = next((item for token, item in PII_HINTS.items() if token in normalized), None)
        detections: list[tuple[str, str, str, float]] = []
        if hint:
            label, sensitivity = hint
            detections.append((label, sensitivity, "column name", 0.9))
        if not values.empty:
            detections.extend(
                [
                    ("Email address", "Restricted", "value pattern", _match_ratio(values, EMAIL_RE.fullmatch)),
                    ("IP address", "Confidential", "value pattern", _match_ratio(values, IP_RE.fullmatch)),
                    ("Phone number", "Restricted", "value pattern", _match_ratio(values, PHONE_RE.fullmatch)),
                    ("Payment card", "Restricted", "Luhn-valid value pattern", _match_ratio(values, lambda value: bool(CARD_RE.fullmatch(value)) and _luhn_valid(value))),
                ]
            )
        viable = [item for item in detections if item[3] >= 0.6]
        if not viable:
            continue
        label, sensitivity, evidence, confidence_score = max(viable, key=lambda item: item[3])
        confidence = "high" if confidence_score >= 0.85 else "medium"
        findings.append(
            DataClassification(
                column=name,
                label=label,
                sensitivity=sensitivity,
                confidence=confidence,
                evidence=evidence,
                recommendation=(
                    "Review access, redact before external sharing, and add an approved handling rule."
                    if sensitivity == "Restricted"
                    else "Review access and document the approved handling policy."
                ),
            )
        )
    return findings


def classifications_frame(classifications: list[DataClassification]) -> pd.DataFrame:
    return pd.DataFrame(
        [asdict(item) for item in classifications],
        columns=["column", "label", "sensitivity", "confidence", "evidence", "recommendation"],
    )


def contract_to_json(contract: DataContract) -> str:
    return json.dumps(contract.to_dict(), ensure_ascii=False, indent=2, default=str)


def contract_from_json(payload: str) -> DataContract:
    return DataContract.from_dict(json.loads(payload))
