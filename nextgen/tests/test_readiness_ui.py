from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from app.composition import build_services
from ui.main_window import MainWindow


_APPLICATION = QApplication.instance() or QApplication([])


def test_main_window_renders_local_data_readiness_insights_without_sample_values(tmp_path):
    window = MainWindow(build_services(tmp_path))

    window._load_sample()
    window._run_data_readiness_insights()

    rendered = window.insights_view.toPlainText()
    assert "Readiness score:" in rendered
    assert "High-cardinality columns:" in rendered
    assert "SO-1001" not in rendered
    assert "Data readiness insights" in window.statusBar().currentMessage()
    window.close()
