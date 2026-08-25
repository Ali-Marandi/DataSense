from PyQt6.QtWidgets import QApplication

from app.composition import build_services
from ui.main_window import MainWindow


def test_main_window_starts_without_a_dataset(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(build_services(tmp_path))
    assert "DataSense" in window.windowTitle()
    window.close()
    assert app is not None
