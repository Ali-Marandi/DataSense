"""Tests for action-scoped, proof-carrying DataSense decision receipts."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd

from core.data_manager import DataManager
from core.decision_receipts import (
    ActionIntent,
    DecisionPolicy,
    action_is_authorized,
    issue_decision_receipt,
    verify_decision_receipt,
)
from core.governance import DataContract, DataQualityRule

KEY = b"decision-receipt-test-secret"
KEY_ID = "local-decision-test"
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def resolver(key_id: str) -> bytes | None:
    return KEY if key_id == KEY_ID else None


def manager(*, duplicate_ids: bool = False) -> DataManager:
    values = ["C-1", "C-1"] if duplicate_ids else ["C-1", "C-2"]
    instance = DataManager(
        df=pd.DataFrame({"customer_id": values, "region": ["Private-North", "Private-South"]}),
        source="/private/customer-export.csv",
    )
    instance.history = []
    instance.set_governance_contract(DataContract("Controlled release", [
        DataQualityRule("unique", "customer_id", severity="high"),
    ]))
    instance.set_schema_baseline()
    instance.run_governance_checks()
    return instance


def receipt_for(action: ActionIntent, *, duplicate_ids: bool = False):
    evidence = manager(duplicate_ids=duplicate_ids).signed_evidence_bundle(KEY, KEY_ID)
    return issue_decision_receipt(
        evidence_bundle=evidence,
        action=action,
        policy=DecisionPolicy(version="pilot-v1", max_receipt_ttl_seconds=900),
        signing_key=KEY,
        key_id=KEY_ID,
        evidence_key_resolver=resolver,
        issued_at=NOW,
    )


def test_internal_trusted_action_receipt_is_signed_private_and_authorized():
    action = ActionIntent("report.html", "internal", "internal_review")
    receipt = receipt_for(action)

    verification = verify_decision_receipt(receipt, resolver, expected_action=action, now=NOW)

    assert verification.valid
    assert verification.outcome == "allow"
    assert action_is_authorized(receipt, resolver, action, now=NOW)
    serialized = json.dumps(receipt, ensure_ascii=False)
    assert "Private-North" not in serialized
    assert "/private/customer-export.csv" not in serialized
    assert receipt["payload"]["privacy"]["contains_raw_dataset_values"] is False


def test_external_action_requires_approval_and_cannot_be_used_as_allow_receipt():
    action = ActionIntent("export.csv", "external", "external_share")
    receipt = receipt_for(action)

    verification = verify_decision_receipt(receipt, resolver, expected_action=action, now=NOW)

    assert verification.valid
    assert verification.outcome == "approval_required"
    assert receipt["payload"]["decision"]["reason_codes"] == ["action_risk_requires_approval"]
    assert not action_is_authorized(receipt, resolver, action, now=NOW)


def test_quality_failure_blocks_even_a_low_risk_action():
    action = ActionIntent("report.html", "internal", "internal_review")
    receipt = receipt_for(action, duplicate_ids=True)

    verification = verify_decision_receipt(receipt, resolver, expected_action=action, now=NOW)

    assert verification.valid
    assert verification.outcome == "block"
    assert "quality_gate_not_approved" in receipt["payload"]["decision"]["reason_codes"]
    assert not action_is_authorized(receipt, resolver, action, now=NOW)


def test_receipt_is_rejected_when_tampered_expired_or_reused_for_another_action():
    action = ActionIntent("report.html", "internal", "internal_review")
    receipt = receipt_for(action)

    changed = json.loads(json.dumps(receipt))
    changed["payload"]["action"]["action_type"] = "agent.external_action"
    assert not verify_decision_receipt(changed, resolver, expected_action=action, now=NOW).valid

    future = NOW + timedelta(seconds=901)
    expired = verify_decision_receipt(receipt, resolver, expected_action=action, now=future)
    assert not expired.valid
    assert "expired" in expired.reason

    other_action = ActionIntent("dashboard.html", "internal", "internal_review")
    mismatch = verify_decision_receipt(receipt, resolver, expected_action=other_action, now=NOW)
    assert not mismatch.valid
    assert "requested action" in mismatch.reason


def test_data_manager_issues_receipt_from_current_governance_state():
    action = ActionIntent("report.html", "internal", "internal_review")
    receipt = manager().signed_decision_receipt(
        action=action,
        policy=DecisionPolicy(version="desktop-v1"),
        signing_key=KEY,
        key_id=KEY_ID,
    )

    verification = verify_decision_receipt(receipt, resolver, expected_action=action)
    assert verification.valid
    assert verification.outcome == "allow"
