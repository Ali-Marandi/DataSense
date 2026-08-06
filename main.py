"""DataSense application entry point."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.version import APP_NAME, APP_PUBLISHER, APP_VERSION
from ui.main_window import MainWindow
from qt_material import apply_stylesheet


def resource_path(*parts: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_PUBLISHER)
    icon = resource_path("assets", "icon.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    window = MainWindow()
    
    # Apply a professional dark theme with custom styling
    extra = {
        'density_scale': '-1',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#28a745',
    }
    apply_stylesheet(app, theme='dark_teal.xml', extra=extra)
    
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
