from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from core.analysis.contracts import ProcessingContext, ProcessingResult
from core.analysis.data_readiness import DataReadinessInsightsModule
from core.data.service import DataService
from core.governance.contracts import DataContract
from core.reporting.automated_report import AutomatedReportConfig, AutomatedReportService


@pytest.fixture
def reporting_inputs():
    data = DataService()
    frame = data.sample_dataset()
    profile = data.profile(frame)
    readiness = DataReadinessInsightsModule().process(frame, ProcessingContext())
    quality = DataContract.default().evaluate(frame)
    return profile, readiness, quality


def _service() -> AutomatedReportService:
    return AutomatedReportService(
        clock=lambda: datetime(2026, 8, 27, 10, 30, tzinfo=timezone.utc),
        report_id_factory=lambda: "report-test-001",
    )


def test_automated_report_writes_html_and_metadata_only_manifest(tmp_path, reporting_inputs):
    profile, readiness, quality = reporting_inputs

    artifact = _service().generate(tmp_path / "daily-report", profile=profile, readiness=readiness, quality=quality)

    assert artifact.artifact_path == tmp_path / "daily-report.html"
    assert artifact.manifest_path == tmp_path / "daily-report.html.manifest.json"
    assert artifact.artifact_path.exists()
    assert artifact.manifest_path.exists()
    assert artifact.report_id == "report-test-001"
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "datasense.automated-report-manifest/v1"
    assert manifest["artifact"]["sha256"] == artifact.sha256
    assert manifest["privacy"] == {"contains_raw_dataset_values": False, "contains_local_source_paths": False}
    assert "SO-1001" not in artifact.artifact_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in artifact.manifest_path.read_text(encoding="utf-8")


def test_automated_report_escapes_column_names_and_limits_aggregate_columns(tmp_path):
    frame = pd.DataFrame({"<danger>&": [1, 2, 3, 4], "segment": ["A", "A", "B", "B"]})
    data = DataService()
    profile = data.profile(frame)
    readiness = DataReadinessInsightsModule().process(frame, ProcessingContext())
    report = AutomatedReportService(
        AutomatedReportConfig(max_column_summaries=1),
        report_id_factory=lambda: "escape-test",
    ).generate(tmp_path / "escaped.html", profile=profile, readiness=readiness)

    text = report.artifact_path.read_text(encoding="utf-8")
    assert "&lt;danger&gt;&amp;" in text
    assert "Showing first 1 aggregate column summaries" in text
    assert "No quality check was supplied" in text


def test_automated_report_rejects_mismatched_or_untrusted_processing_result(tmp_path, reporting_inputs):
    profile, readiness, quality = reporting_inputs
    wrong_module = ProcessingResult(module_id="other-module/v1", summary=readiness.summary)
    wrong_shape = ProcessingResult(
        module_id="data-readiness-insights/v1",
        summary={**readiness.summary, "rows": profile.rows + 1},
    )

    with pytest.raises(ValueError, match="requires data-readiness"):
        _service().generate(tmp_path / "x", profile=profile, readiness=wrong_module, quality=quality)
    with pytest.raises(ValueError, match="does not match"):
        _service().generate(tmp_path / "x", profile=profile, readiness=wrong_shape, quality=quality)


def test_automated_report_validates_configuration_and_score(tmp_path, reporting_inputs):
    profile, readiness, _quality = reporting_inputs
    invalid_score = ProcessingResult(
        module_id="data-readiness-insights/v1",
        summary={**readiness.summary, "readiness_score": 101},
    )

    with pytest.raises(ValueError, match="max_column"):
        AutomatedReportConfig(max_column_summaries=0)
    with pytest.raises(ValueError, match="Readiness score"):
        _service().generate(tmp_path / "x", profile=profile, readiness=invalid_score)


def test_automated_report_marks_blocked_quality_without_blocking_aggregate_report(tmp_path, reporting_inputs):
    profile, readiness, _quality = reporting_inputs
    frame = DataService().sample_dataset()
    frame.loc[1, "order_id"] = "SO-1001"
    blocked_quality = DataContract.default().evaluate(frame)

    artifact = _service().generate(tmp_path / "blocked", profile=profile, readiness=readiness, quality=blocked_quality)

    assert artifact.quality_status == "blocked"
    assert "Quality evidence · blocked" in artifact.artifact_path.read_text(encoding="utf-8")


def test_automated_report_preserves_existing_artifact_and_cleans_temp_on_replace_error(tmp_path, reporting_inputs, monkeypatch):
    profile, readiness, quality = reporting_inputs
    destination = tmp_path / "existing.html"
    destination.write_text("previous artifact", encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("core.reporting.automated_report.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        _service().generate(destination, profile=profile, readiness=readiness, quality=quality)

    assert destination.read_text(encoding="utf-8") == "previous artifact"
    assert list(tmp_path.glob("*.tmp")) == []


def test_standard_reporting_and_verified_delivery_keep_distinct_quality_policies(tmp_path):
    from core.delivery.signing import InMemoryHmacSigningKeyProvider
    from core.delivery.verified_export import VerifiedExportService

    data = DataService()
    frame = data.sample_dataset()
    frame.loc[1, "order_id"] = "SO-1001"
    profile = data.profile(frame)
    readiness = DataReadinessInsightsModule().process(frame, ProcessingContext())
    blocked_quality = DataContract.default().evaluate(frame)

    standard = _service().generate(tmp_path / "standard", profile=profile, readiness=readiness, quality=blocked_quality)
    verified = VerifiedExportService().export_html(
        tmp_path / "verified.html",
        frame,
        profile,
        blocked_quality,
        InMemoryHmacSigningKeyProvider(b"test-signing-key-at-least-32-bytes"),
    )

    assert standard.artifact_path.exists()
    assert standard.quality_status == "blocked"
    assert not verified.decision.approved
    assert verified.artifact_path is None
    assert verified.receipt_path.exists()
