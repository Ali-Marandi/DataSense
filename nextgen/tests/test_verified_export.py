from __future__ import annotations

import json

import pytest

from core.data.service import DataService
from core.delivery.signing import InMemoryHmacSigningKeyProvider
from core.delivery.verified_export import VerifiedExportService
from core.governance.contracts import DataContract


@pytest.fixture
def signing_provider() -> InMemoryHmacSigningKeyProvider:
    return InMemoryHmacSigningKeyProvider(b"test-signing-key-at-least-32-bytes")


def test_verified_export_writes_artifact_and_verifiable_metadata_only_receipt(tmp_path, signing_provider):
    service = DataService()
    frame = service.sample_dataset()
    profile = service.profile(frame)
    quality = DataContract.default().evaluate(frame)
    destination = tmp_path / "report.html"

    result = VerifiedExportService().export_html(destination, frame, profile, quality, signing_provider)

    assert result.decision.approved
    assert result.artifact_path == destination
    assert destination.exists()
    assert result.receipt_path.exists()
    assert VerifiedExportService().verify_receipt(result.receipt_path, signing_provider)
    receipt_text = result.receipt_path.read_text(encoding="utf-8")
    assert "SO-1001" not in receipt_text
    assert str(tmp_path) not in receipt_text
    assert "Receipt SHA-256" in destination.read_text(encoding="utf-8")


def test_blocked_export_writes_signed_decision_receipt_but_not_artifact(tmp_path, signing_provider):
    service = DataService()
    frame = service.sample_dataset()
    frame.loc[1, "order_id"] = "SO-1001"
    profile = service.profile(frame)
    quality = DataContract.default().evaluate(frame)
    destination = tmp_path / "report.html"

    result = VerifiedExportService().export_html(destination, frame, profile, quality, signing_provider)

    assert not result.decision.approved
    assert result.artifact_path is None
    assert result.receipt_path.exists()
    assert not destination.exists()
    assert VerifiedExportService().verify_receipt(result.receipt_path, signing_provider)


def test_receipt_tampering_is_detected(tmp_path, signing_provider):
    service = DataService()
    frame = service.sample_dataset()
    profile = service.profile(frame)
    quality = DataContract.default().evaluate(frame)
    result = VerifiedExportService().export_html(tmp_path / "report.html", frame, profile, quality, signing_provider)

    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    receipt["payload"]["dataset"]["rows"] = 999
    result.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    assert not VerifiedExportService().verify_receipt(result.receipt_path, signing_provider)


def test_export_rejects_profile_that_does_not_match_frame(tmp_path, signing_provider):
    service = DataService()
    frame = service.sample_dataset()
    profile = service.profile(frame.iloc[:2])
    quality = DataContract.default().evaluate(frame)

    with pytest.raises(ValueError, match="does not match"):
        VerifiedExportService().export_html(tmp_path / "report.html", frame, profile, quality, signing_provider)


def test_export_normalizes_missing_html_suffix(tmp_path, signing_provider):
    service = DataService()
    frame = service.sample_dataset()
    profile = service.profile(frame)
    quality = DataContract.default().evaluate(frame)

    result = VerifiedExportService().export_html(tmp_path / "report", frame, profile, quality, signing_provider)

    assert result.artifact_path == tmp_path / "report.html"
