from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication

APP_NAME = "DataSense"
APP_VERSION = "0.1.0-alpha"


def app_data_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging() -> None:
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(log_dir / "datasense.log", encoding="utf-8")],
    )


def create_application(argv: list[str] | None = None) -> QApplication:
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(argv or [])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("DataSense")
    app.setApplicationVersion(APP_VERSION)
    configure_logging()
    return app
