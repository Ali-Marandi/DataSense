from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication

from app.observability import Observability, configure_observability

APP_NAME = "DataSense"
APP_VERSION = "0.1.0-alpha"


def app_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging(base_dir: Path | None = None) -> Observability:
    """Configure redacted, rotating local logs and return the injected service."""
    return configure_observability(base_dir or app_data_dir())


def create_application(argv: list[str] | None = None) -> QApplication:
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(argv or [])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("DataSense")
    app.setApplicationVersion(APP_VERSION)
    observability = configure_logging()
    observability.error_monitor.install_global_handlers()
    app.datasense_observability = observability  # type: ignore[attr-defined]
    return app
