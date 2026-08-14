"""Tests for DataSense signed, metadata-only evidence bundles."""
from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd

from core.data_manager import DataManager
from core.evidence import (
    build_evidence_payload,
    read_evidence_bundle,
    sign_evidence_payload,
    verify_evidence_bundle,
    write_evidence_bundle,
)
from core.governance import DataContract, DataQualityRule


def _manager() -> DataManager:
    manager = DataManager(
        df=pd.DataFrame(
            {
                "customer_id": ["C-1", "C-2"],
                "email": ["alice@example.com", "bob@example.com"],
                "region": ["Private-North", "Private-South"],
            }
        ),
        source="/private/customer-export.csv",
    )
    manager.history = []
    manager.set_governance_contract(
        DataContract(
            "Controlled release",
            [
                DataQualityRule("unique", "customer_id", severity="high"),
                DataQualityRule(
                    "allowed_values",
                    "region",
                    {"values": ["Private-North", "Private-South"]},
                    severity="medium",
                ),
            ],
        )
    )
    manager.set_schema_baseline()
    manager.run_governance_checks()
    return manager


def test_signed_bundle_is_metadata_only_and_verifies():
    manager = _manager()

    bundle = manager.signed_evidence_bundle(b"local-test-secret", "pilot-hmac-2026")
    verification = verify_evidence_bundle(
        bundle,
        lambda key_id: b"local-test-secret" if key_id == "pilot-hmac-2026" else None,
    )

    assert verification.valid
    assert bundle["signature"]["algorithm"] == "HMAC-SHA256"
    serialized = json.dumps(bundle, ensure_ascii=False)
    assert "alice@example.com" not in serialized
    assert "bob@example.com" not in serialized
    assert "Private-North" not in serialized
    assert "/private/customer-export.csv" not in serialized
    assert bundle["payload"]["privacy"]["contains_raw_dataset_values"] is False


def test_tampered_bundle_fails_canonical_verification():
    manager = _manager()
    bundle = manager.signed_evidence_bundle(b"local-test-secret", "pilot-hmac-2026")
    bundle["payload"]["quality_report"]["rows"] = 99

    verification = verify_evidence_bundle(bundle, lambda _key_id: b"local-test-secret")

    assert not verification.valid
    assert "digest" in verification.reason.lower()


def test_canonical_signing_is_stable_for_different_mapping_order():
    first = {"schema": "demo", "details": {"b": 2, "a": 1}}
    second = {"details": {"a": 1, "b": 2}, "schema": "demo"}

    one = sign_evidence_payload(first, b"key", "key-1")
    two = sign_evidence_payload(second, b"key", "key-1")

    assert one["payload_sha256"] == two["payload_sha256"]
    assert one["signature"]["value"] == two["signature"]["value"]


def test_verify_command_reads_bundle_and_key_file(tmp_path):
    manager = _manager()
    key_file = tmp_path / "pilot-hmac.key"
    key_file.write_bytes(b"cli-test-secret\n")
    bundle_path = tmp_path / "evidence.signed.json"
    write_evidence_bundle(bundle_path, manager.signed_evidence_bundle(b"cli-test-secret", "pilot-hmac"))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.evidence",
            str(bundle_path),
            "--key-file",
            str(key_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["valid"] is True
    assert read_evidence_bundle(bundle_path)["signature"]["key_id"] == "pilot-hmac"


def test_payload_build_uses_explicit_timestamp_for_reproducible_evidence():
    manager = _manager()
    payload = build_evidence_payload(
        report=manager.governance_report,
        contract=manager.governance_contract,
        gate_policy=manager.quality_gate_policy,
        quality_history=manager.quality_history,
        schema_baseline=manager.schema_baseline,
        schema_drift_policy=manager.schema_drift_policy,
        schema_drift_report=manager.check_schema_drift(),
        lineage=manager.lineage,
        generated_at="2026-08-14T00:00:00+00:00",
    )

    assert payload["generated_at"] == "2026-08-14T00:00:00+00:00"
    assert payload["schema"] == "datasense.evidence-bundle/v1"
