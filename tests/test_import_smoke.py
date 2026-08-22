"""Smoke tests that keep optional workspaces importable in packaged builds."""

import importlib

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
