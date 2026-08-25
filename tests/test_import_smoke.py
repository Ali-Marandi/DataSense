"""Smoke tests that keep optional workspaces importable in packaged builds."""

import importlib

import pandas as pd
import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "core.security",
        "core.db_connector",
        "core.ai_assistant",
        "ui.security_tab",
        "ui.db_tab",
        "ui.main_window",
    ],
)
def test_workspace_modules_import(module_name):
    """Every shipped workspace must load before a user opens it."""
    importlib.import_module(module_name)


def test_main_window_exposes_trust_center():
    """The packaged desktop shell must expose the governance workspace."""
    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.tabs.tabText(window.tabs.indexOf(window.trust_center_tab)) == "Trust Center"
    assert window.trust_center_tab.receipt_export_button.text() == "Issue trust decision receipt"
    window.close()
    assert app is not None


def _governed_manager(*, duplicate_ids: bool = False):
    from core.data_manager import DataManager
    from core.governance import DataContract, DataQualityRule

    values = ["A-100", "A-100"] if duplicate_ids else ["A-100", "A-101"]
    manager = DataManager(df=pd.DataFrame({"order_id": values, "revenue": [120.0, 150.0]}), source="orders.csv")
    manager.history = []
    manager.set_governance_contract(DataContract("Verified export", [
        DataQualityRule("unique", "order_id", severity="high"),
    ]))
    manager.set_schema_baseline()
    manager.run_governance_checks()
    return manager


def _configure_verified_export_dialogs(monkeypatch, artifact_path, key_path):
    from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

    monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("Analysis report (HTML)", True))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(artifact_path), "HTML files (*.html)"))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(key_path), "Key files (*.key)"))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)


def test_verified_report_writes_artifact_and_metadata_only_receipt(tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    artifact_path = tmp_path / "verified-report.html"
    key_path = tmp_path / "local-export.key"
    key_path.write_bytes(b"trusted-export-test-key")
    _configure_verified_export_dialogs(monkeypatch, artifact_path, key_path)

    window = MainWindow()
    window.manager = _governed_manager()
    window.export_verified_artifact()

    receipt_path = tmp_path / "verified-report.html.trust-receipt.json"
    assert artifact_path.exists()
    assert receipt_path.exists()
    assert "A-100" not in receipt_path.read_text(encoding="utf-8")
    assert '"outcome": "allow"' in receipt_path.read_text(encoding="utf-8")
    window.close()
    assert app is not None


def test_verified_report_is_not_written_when_quality_gate_blocks(tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    artifact_path = tmp_path / "blocked-report.html"
    key_path = tmp_path / "local-export.key"
    key_path.write_bytes(b"trusted-export-test-key")
    _configure_verified_export_dialogs(monkeypatch, artifact_path, key_path)

    window = MainWindow()
    window.manager = _governed_manager(duplicate_ids=True)
    window.export_verified_artifact()

    receipt_path = tmp_path / "blocked-report.html.trust-receipt.json"
    assert not artifact_path.exists()
    assert receipt_path.exists()
    assert '"outcome": "block"' in receipt_path.read_text(encoding="utf-8")
    window.close()
    assert app is not None
