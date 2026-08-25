from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from app.composition import build_services
from ui.dashboard_panel import DashboardPanel
from ui.main_window import MainWindow


_APPLICATION = QApplication.instance() or QApplication([])


def _app() -> QApplication:
    return _APPLICATION


def test_dashboard_renders_local_profile_and_approved_trust_state(tmp_path):
    _app()
    services = build_services(tmp_path)
    frame = services.data.sample_dataset()
    profile = services.data.profile(frame)
    quality = services.state.contract.evaluate(frame)
    panel = DashboardPanel()

    panel.update_dashboard(profile, quality, "Sample operations")

    assert panel.metric_cards["rows"].value.text() == "4"
    assert panel.metric_cards["columns"].value.text() == "4"
    assert panel.columns_table.rowCount() == 4
    assert panel.trust_badge.text() == "VERIFIED\nREADY"
    assert panel.quality_progress.value() == 100
    panel.close()


def test_dashboard_renders_blocked_state_without_raw_values(tmp_path):
    _app()
    services = build_services(tmp_path)
    frame = services.data.sample_dataset()
    frame.loc[1, "order_id"] = "SO-1001"
    profile = services.data.profile(frame)
    quality = services.state.contract.evaluate(frame)
    panel = DashboardPanel()

    panel.update_dashboard(profile, quality, "Sensitive customer file")

    assert panel.trust_badge.text() == "ACTION\nREQUIRED"
    assert "blocking" in panel.quality_progress.text().lower()
    assert "SO-1001" not in panel.health_label.text()
    panel.close()


def test_main_window_connects_sample_flow_to_dashboard_and_quality_table(tmp_path):
    _app()
    window = MainWindow(build_services(tmp_path))

    window._load_sample()
    window._run_quality_checks()

    assert window.preview_table.rowCount() == 4
    assert window.quality_table.rowCount() == 2
    assert window.dashboard.metric_cards["rows"].value.text() == "4"
    assert "approved" in window.quality_summary.text()
    window.close()
