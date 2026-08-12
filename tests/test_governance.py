"""Tests for deterministic Trust Center behaviour."""

import json

import pandas as pd

from core.data_manager import DataManager
from core.governance import (
    DataContract,
    DataQualityRule,
    contract_from_json,
    contract_to_json,
    recommended_rules,
    scan_sensitive_data,
)
from core.project import load_project, save_project


def sample_frame():
    return pd.DataFrame(
        {
            "customer_id": ["C-1", "C-2", "C-2", None],
            "region": ["North", "South", "Unknown", "South"],
            "revenue": [120.0, -5.0, 40.0, 60.0],
            "email": ["a@example.com", "b@example.com", "bad", None],
            "event_date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        }
    )


def test_contract_reports_each_rule_without_mutating_data():
    frame = sample_frame()
    original = frame.copy(deep=True)
    contract = DataContract(
        "Sales acceptance",
        [
            DataQualityRule("not_null", "customer_id", severity="critical"),
            DataQualityRule("unique", "customer_id", severity="high"),
            DataQualityRule("range", "revenue", {"min": 0}, severity="high"),
            DataQualityRule("allowed_values", "region", {"values": ["North", "South"]}),
            DataQualityRule("regex", "email", {"pattern": r"[^@]+@[^@]+\.[^@]+"}),
        ],
    )

    report = contract.execute(frame)

    assert len(report.results) == 5
    assert {result.status for result in report.results} == {"fail"}
    assert report.status == "blocked"
    assert report.score == 0.0
    pd.testing.assert_frame_equal(frame, original)
    assert set(report.to_frame()["column"]) == {"customer_id", "revenue", "region", "email"}


def test_empty_contract_does_not_claim_a_perfect_score():
    report = DataContract().execute(sample_frame())

    assert report.score is None
    assert report.status == "not configured"
    assert report.summary()["Score"] == "Not configured"


def test_contract_is_json_portable():
    contract = DataContract("Contract", [DataQualityRule("range", "revenue", {"min": 0}, "high")])

    restored = contract_from_json(contract_to_json(contract))

    assert restored == contract
    assert json.loads(contract_to_json(contract))["name"] == "Contract"


def test_sensitive_data_scan_retains_only_metadata():
    findings = scan_sensitive_data(sample_frame())

    email = next(finding for finding in findings if finding.column == "email")
    assert email.label == "Email address"
    assert email.sensitivity == "Restricted"
    assert "a@example.com" not in str(email)


def test_recommended_rules_are_reviewable_and_conservative():
    rules = recommended_rules(pd.DataFrame({"order_id": ["1", "2", "3"], "region": ["North", "South", "North"]}))

    assert any(rule.rule_type == "not_null" and rule.column == "order_id" for rule in rules)
    assert any(rule.rule_type == "unique" and rule.column == "order_id" for rule in rules)
    assert any(rule.rule_type == "allowed_values" and rule.column == "region" for rule in rules)


def test_manager_invalidates_stale_report_after_mutation():
    manager = DataManager(df=pd.DataFrame({"id": [1, 2]}))
    manager.set_governance_contract(DataContract(rules=[DataQualityRule("unique", "id")]))
    manager.run_governance_checks()

    manager.set_frame(pd.DataFrame({"id": [1, 1]}), "Changed rows")

    assert manager.governance_report is None


def test_project_round_trip_keeps_contract_but_requires_rerun(tmp_path):
    manager = DataManager(df=pd.DataFrame({"id": [1, 2]}), source="memory")
    manager.history = []
    manager.set_governance_contract(DataContract("Key contract", [DataQualityRule("unique", "id")]))
    path = tmp_path / "project.dsproj"

    ok, message = save_project(manager, str(path))
    restored = DataManager()
    loaded, load_message = load_project(restored, str(path))

    assert ok, message
    assert loaded, load_message
    assert restored.governance_contract.name == "Key contract"
    assert restored.governance_contract.rules[0].rule_type == "unique"
    assert restored.governance_report is None


def test_quality_gate_blocks_low_score_and_critical_failure():
    from core.governance import QualityGatePolicy

    report = DataContract(
        "Sales gate",
        [DataQualityRule("not_null", "customer_id", severity="critical")],
    ).execute(sample_frame())

    decision = report.gate_decision(QualityGatePolicy(name="Release gate", minimum_score=99.0))

    assert decision.decision == "blocked"
    assert decision.score == 0.0
    assert any("critical" in reason for reason in decision.reasons)


def test_quality_history_tracks_only_quality_metadata_and_direction():
    from core.governance import QualityHistory

    contract = DataContract("Trend", [DataQualityRule("unique", "customer_id", severity="high")])
    history = QualityHistory()
    first = contract.execute(pd.DataFrame({"customer_id": ["A", "A"]}))
    history.add(first, first.gate_decision())
    second = contract.execute(pd.DataFrame({"customer_id": ["A", "B"]}))
    history.add(second, second.gate_decision())

    assert history.trend() == "improving"
    exported = history.to_dict()
    assert exported["records"][-1]["score"] == 100.0
    assert "customer_id" not in str(exported)


def test_project_round_trip_keeps_quality_policy_and_history(tmp_path):
    from core.governance import QualityGatePolicy

    manager = DataManager(df=pd.DataFrame({"id": [1, 2]}), source="memory")
    manager.history = []
    manager.set_governance_contract(DataContract("Key contract", [DataQualityRule("unique", "id")]))
    manager.set_quality_gate_policy(QualityGatePolicy(name="Controlled release", minimum_score=100.0))
    manager.run_governance_checks()
    path = tmp_path / "project.dsproj"

    assert save_project(manager, str(path))[0]
    restored = DataManager()
    assert load_project(restored, str(path))[0]
    assert restored.quality_gate_policy.name == "Controlled release"
    assert len(restored.quality_history.records) == 1
    assert restored.quality_history.records[0].gate_decision == "approved"


def test_schema_drift_blocks_breaking_dtype_and_nullability_changes_without_retaining_values():
    manager = DataManager(df=pd.DataFrame({"customer_id": ["A", "B"], "amount": [1, 2]}))
    baseline = manager.set_schema_baseline()

    manager.set_frame(
        pd.DataFrame({"customer_id": [1, 2], "amount": [1, None], "region": ["N", "S"]}),
        "Simulated upstream schema change",
    )
    report = manager.check_schema_drift()

    assert report.decision == "blocked"
    assert report.added_columns == ("region",)
    assert set(report.dtype_changes) == {"customer_id", "amount"}
    assert report.nullability_relaxations == ("amount",)
    schema_evidence = str(baseline.to_dict())
    assert "'A'" not in schema_evidence
    assert "'B'" not in schema_evidence


def test_schema_drift_policy_can_reject_additive_columns_and_persists_with_project(tmp_path):
    from core.governance import SchemaDriftPolicy

    manager = DataManager(df=pd.DataFrame({"id": [1, 2]}), source="memory")
    manager.history = []
    manager.set_schema_baseline()
    manager.set_schema_drift_policy(SchemaDriftPolicy(name="Strict schema", allow_added_columns=False))
    manager.set_frame(pd.DataFrame({"id": [1, 2], "country": ["IR", "DE"]}), "Added country")

    assert manager.check_schema_drift().decision == "blocked"
    path = tmp_path / "schema.dsproj"
    assert save_project(manager, str(path))[0]
    restored = DataManager()
    assert load_project(restored, str(path))[0]
    assert restored.schema_baseline is not None
    assert restored.schema_drift_policy.name == "Strict schema"
    assert restored.check_schema_drift().decision == "blocked"
