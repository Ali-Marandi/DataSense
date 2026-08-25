"""DataSense main window: navigation, session commands and reporting."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from core.data_manager import DataManager, SUPPORTED_IMPORT
from core.decision_receipts import ActionIntent, DecisionPolicy, action_is_authorized, write_decision_receipt
from core.evidence import read_signing_key
from core.version import APP_NAME, APP_VERSION, APP_TAGLINE, APP_PUBLISHER, APP_URL
from core.project import load_project, save_project
from core.report import ReportBuilder
from ui.visualization_tab import VisualizationTab
from ui.analysis_tab import AnalysisTab
from ui.db_tab import DBTab
from ui.cleaning_tab import CleaningTab
from ui.automl_tab import AutoMLTab
from ui.report_tab import ReportTab
from ui.ai_assistant_tab import AIAssistantTab
from ui.security_tab import SecurityTab
from ui.streaming_tab import StreamingTab
from ui.data_tab import DataTab
from ui.transform_tab import TransformTab
from ui.ml_tab import MLTab
from ui.overview_tab import OverviewTab
from ui.sql_tab import SQLTab
from ui.timeseries_tab import TimeSeriesTab
from ui.dashboard_tab import DashboardTab
from ui.trust_center_tab import TrustCenterTab
from core.dashboard import build_dashboard
from ui.theme import stylesheet

IMPORT_FILTER = ";;".join(
    [f"{desc} (*{ext})" for ext, desc in SUPPORTED_IMPORT.items()]
)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("DataSense", "DataSense")
        self.dark = bool(self.settings.value("dark", True, type=bool))
        self.manager = DataManager()
        self.recent: list[str] = list(self.settings.value("recent", [], type=list) or [])
        self.analysis_log: list[tuple[str, pd.DataFrame | None]] = []

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1440, 900)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_tabs()
        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_status()
        self.apply_theme()
        self.refresh_all()

    # ------------------------------------------------------------------ build
    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Original Tabs
        self.overview_tab = OverviewTab(self.manager)
        self.sql_tab = SQLTab(self.manager)
        self.timeseries_tab = TimeSeriesTab(self.manager)
        self.dashboard_tab = DashboardTab(self.manager)
        self.data_tab = DataTab(self.manager)
        self.transform_tab = TransformTab(self.manager)
        self.analysis_tab = AnalysisTab(self.manager)
        self.viz_tab = VisualizationTab(self.manager, self.dark)
        self.ml_tab = MLTab(self.manager)
        
        # New Advanced Tabs
        self.db_tab = DBTab(self.manager)
        self.cleaning_tab = CleaningTab(self.manager)
        self.automl_tab = AutoMLTab(self.manager)
        self.report_tab = ReportTab(self.manager)
        self.ai_assistant_tab = AIAssistantTab(self.manager)
        self.security_tab = SecurityTab(self.manager)
        self.streaming_tab = StreamingTab(self.manager)
        self.trust_center_tab = TrustCenterTab(self.manager)

        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.sql_tab, "SQL Console")
        self.tabs.addTab(self.db_tab, "SQL Database")
        self.tabs.addTab(self.transform_tab, "Prepare")
        self.tabs.addTab(self.cleaning_tab, "Smart Cleaning")
        self.tabs.addTab(self.analysis_tab, "Statistics")
        self.tabs.addTab(self.viz_tab, "Visualise")
        self.tabs.addTab(self.timeseries_tab, "Time Series")
        self.tabs.addTab(self.ml_tab, "Machine Learning")
        self.tabs.addTab(self.automl_tab, "AutoML (AI)")
        self.tabs.addTab(self.ai_assistant_tab, "AI Assistant")
        self.tabs.addTab(self.security_tab, "Security & Versions")
        self.tabs.addTab(self.trust_center_tab, "Trust Center")
        self.tabs.addTab(self.streaming_tab, "Live Streaming")
        self.tabs.addTab(self.dashboard_tab, "Dashboards")
        self.tabs.addTab(self.report_tab, "Report Generator")

        self.setCentralWidget(self.tabs)

        self.data_tab.dataChanged.connect(self.refresh_all)
        self.transform_tab.dataChanged.connect(self.refresh_all)
        self.analysis_tab.resultReady.connect(self._log_result)
        self.ml_tab.resultReady.connect(self._log_result)
        self.sql_tab.dataChanged.connect(self.refresh_all)
        self.sql_tab.resultReady.connect(self._log_result)
        self.timeseries_tab.resultReady.connect(self._log_result)

    def _build_actions(self) -> None:
        def action(text: str, slot, shortcut: str | None = None, tip: str = "") -> QAction:
            act = QAction(text, self)
            act.triggered.connect(slot)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            act.setStatusTip(tip or text)
            return act
        
        self.act_quit = action("&Quit", self.close, "Ctrl+Q", "Exit the application")
        self.act_import = action("&Import data...", self.import_data, "Ctrl+I", "Import CSV, Excel or JSON")
        self.act_sample = action("Load &sample", self.load_sample, "Ctrl+L", "Load retail sample dataset")
        self.act_undo = action("&Undo", self.undo, "Ctrl+Z", "Revert last transformation")
        self.act_redo = action("&Redo", self.redo, "Ctrl+Y", "Reapply transformation")
        self.act_export = action("&Export data...", self.export_data, "Ctrl+E", "Save active dataset")
        self.act_report = action("Export &report...", self.export_report, "Ctrl+R", "Generate HTML report")
        self.act_dashboard = action("Export &dashboard...", self.export_dashboard, "Ctrl+D", "Generate interactive dashboard")
        self.act_verified_export = action(
            "Export &verified artifact...",
            self.export_verified_artifact,
            "Ctrl+Shift+E",
            "Create a report or dashboard only after local Trust Center gates allow it",
        )
        self.act_theme = action("&Toggle theme", self.toggle_theme, "Ctrl+T", "Switch dark/light mode")
        self.act_about = action("&About", self.show_about, None, "Show application info")
        self.act_open_project = action("&Open project...", self.open_project, "Ctrl+O", "Load a saved project")
        self.act_save_project = action("&Save project...", self.save_project_as, "Ctrl+S", "Save current state")

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        file_menu.addActions([self.act_import, self.act_sample])
        self.recent_menu = file_menu.addMenu("Recent files")
        file_menu.addSeparator()
        file_menu.addActions([self.act_open_project, self.act_save_project])
        file_menu.addSeparator()
        file_menu.addActions([self.act_export, self.act_report, self.act_dashboard, self.act_verified_export])
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)

        edit_menu = bar.addMenu("&Edit")
        edit_menu.addActions([self.act_undo, self.act_redo])

        view_menu = bar.addMenu("&View")
        view_menu.addAction(self.act_theme)
        for index in range(self.tabs.count()):
            title = self.tabs.tabText(index)
            act = QAction(title, self)
            act.setShortcut(QKeySequence(f"Ctrl+{index + 1}"))
            act.triggered.connect(lambda _=False, i=index: self.tabs.setCurrentIndex(i))
            view_menu.addAction(act)

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(self.act_about)
        self._refresh_recent_menu()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.addActions([self.act_import, self.act_sample])
        toolbar.addSeparator()
        toolbar.addActions([self.act_undo, self.act_redo])
        toolbar.addSeparator()
        toolbar.addActions([self.act_export, self.act_report, self.act_dashboard, self.act_verified_export, self.act_theme])
        self.addToolBar(toolbar)

    def _build_status(self) -> None:
        self.status_dataset = QLabel("No dataset loaded")
        self.status_shape = QLabel("")
        bar = self.statusBar()
        bar.addWidget(self.status_dataset, 1)
        bar.addPermanentWidget(self.status_shape)
        bar.showMessage(f"{APP_NAME} {APP_VERSION} ready", 5000)

    # ---------------------------------------------------------------- session
    def import_data(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import data", "", IMPORT_FILTER)
        if path:
            self._load_path(path)

    def _load_path(self, path: str) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        ok, message = self.manager.load(path)
        QApplication.restoreOverrideCursor()
        if not ok:
            QMessageBox.critical(self, "Import failed", message)
            return
        self.recent = [path] + [p for p in self.recent if p != path][:7]
        self.settings.setValue("recent", self.recent)
        self._refresh_recent_menu()
        self.analysis_log.clear()
        self.refresh_all()
        self.statusBar().showMessage(message, 8000)

    def load_sample(self) -> None:
        rng = np.random.default_rng(7)
        n = 900
        region = rng.choice(["North", "South", "East", "West"], n)
        channel = rng.choice(["Retail", "Online", "Wholesale"], n, p=[0.4, 0.45, 0.15])
        units = rng.integers(1, 60, n)
        unit_price = np.round(rng.normal(48, 12, n).clip(8, None), 2)
        discount = np.round(rng.beta(2, 8, n) * 0.4, 3)
        revenue = np.round(units * unit_price * (1 - discount), 2)
        satisfaction = np.round((revenue / revenue.max() * 3 + rng.normal(6, 1.1, n)).clip(1, 10), 2)
        frame = pd.DataFrame(
            {
                "order_date": pd.date_range("2024-01-01", periods=n, freq="8h"),
                "region": region,
                "channel": channel,
                "units": units,
                "unit_price": unit_price,
                "discount": discount,
                "revenue": revenue,
                "delivery_days": rng.integers(1, 12, n),
                "satisfaction": satisfaction,
                "returned": rng.choice(["yes", "no"], n, p=[0.12, 0.88]),
            }
        )
        frame.loc[rng.choice(n, 40, replace=False), "satisfaction"] = np.nan
        self.manager.source = "Sample retail dataset"
        self.manager.history = []
        self.manager.set_frame(frame, "Loaded sample dataset")
        self.analysis_log.clear()
        self.refresh_all()
        self.statusBar().showMessage("Sample retail dataset loaded (900 rows)", 8000)

    def export_data(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export dataset", "dataset.csv",
            "CSV (*.csv);;Excel (*.xlsx);;JSON (*.json);;Parquet (*.parquet)"
        )
        if not path:
            return
        ok, message = self.manager.export(path)
        (self.statusBar().showMessage(message, 8000) if ok
         else QMessageBox.critical(self, "Export failed", message))

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "DataSense project (*.dsproj)")
        if not path:
            return
        ok, message = load_project(self.manager, path)
        if not ok:
            QMessageBox.critical(self, "Could not open project", message)
            return
        self.refresh_all()
        self.statusBar().showMessage(message, 8000)

    def save_project_as(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", "analysis.dsproj", "DataSense project (*.dsproj)"
        )
        if not path:
            return
        ok, message = save_project(self.manager, path)
        (self.statusBar().showMessage(message, 8000) if ok
         else QMessageBox.critical(self, "Could not save project", message))

    def _save_report(self, path: str) -> None:
        """Build a styled report from the active session without altering the dataset."""
        report = ReportBuilder(
            title=f"{APP_NAME} analysis report",
            subtitle=os.path.basename(self.manager.source or "in-memory dataset"),
        )
        df = self.manager.df
        report.add_metrics(
            "Dataset overview",
            {
                "Rows": f"{len(df):,}",
                "Columns": df.shape[1],
                "Missing cells": f"{int(df.isna().sum().sum()):,}",
                "Duplicate rows": f"{int(df.duplicated().sum()):,}",
                "Memory": f"{self.manager.memory_usage_mb():.2f} MB",
            },
        )
        report.add_table("Column quality profile", self.manager.profile())
        if self.manager.governance_report is not None:
            report.add_metrics("Trust Center summary", self.manager.governance_report.summary())
            report.add_table("Data contract results", self.manager.governance_report.to_frame())
        report.add_table("Data sample", df.head(25))
        for title, frame in self.analysis_log:
            if frame is not None and not frame.empty:
                report.add_table(title, frame)
        try:
            report.add_figure("Latest chart", self.viz_tab.canvas.figure)
        except Exception:
            pass
        steps = "; ".join(step.label for step in self.manager.history)
        report.add_text("Processing steps", steps or "No transformations applied.")
        report.save(path)

    def export_report(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export report", "datasense-report.html", "HTML report (*.html)"
        )
        if not path:
            return
        try:
            self._save_report(path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Report export failed", str(exc))
            return
        self.statusBar().showMessage(f"Report exported to {path}", 8000)

    def export_dashboard(self) -> None:
        if not self._require_data():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export dashboard", "datasense-dashboard.html", "HTML dashboard (*.html)"
        )
        if not path:
            return
        ok, message = build_dashboard(
            self.manager.df, path,
            title=f"{APP_NAME} dashboard",
            subtitle=os.path.basename(self.manager.source or "in-memory dataset"),
        )
        (self.statusBar().showMessage(message, 8000) if ok
         else QMessageBox.critical(self, "Dashboard failed", message))

    def export_verified_artifact(self) -> None:
        """Export a locally authorized report or dashboard with a signed trust receipt.

        A verified export never transmits data and is available only after the current
        Trust Center report passes its quality and schema gates.  The companion receipt
        is metadata-only, expires automatically and remains useful for offline review.
        """
        if not self._require_data():
            return
        if self.manager.governance_report is None:
            QMessageBox.information(
                self,
                "Run Trust Center checks first",
                "Verified export requires current local quality checks. Open Trust Center, configure any "
                "required rules and run the checks before exporting.",
            )
            return
        labels = ["Analysis report (HTML)", "Interactive dashboard (HTML)"]
        label, accepted = QInputDialog.getItem(
            self, "Verified export", "Artifact", labels, 0, False
        )
        if not accepted:
            return
        is_report = label == labels[0]
        action = ActionIntent(
            "report.html" if is_report else "dashboard.html",
            "internal",
            "internal_review",
        )
        default_name = "datasense-verified-report.html" if is_report else "datasense-verified-dashboard.html"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save verified artifact",
            default_name,
            "HTML files (*.html)",
        )
        if not path:
            return
        key_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose local HMAC signing key",
            "",
            "Key files (*.key *.secret *.txt);;All files (*)",
        )
        if not key_path:
            return
        receipt_path = str(Path(path).with_suffix(Path(path).suffix + ".trust-receipt.json"))
        try:
            key = read_signing_key(key_path)
            key_id = Path(key_path).stem
            receipt = self.manager.signed_decision_receipt(
                action=action,
                policy=DecisionPolicy(version="desktop-v1"),
                signing_key=key,
                key_id=key_id,
            )
            write_decision_receipt(receipt_path, receipt)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Verified export failed", str(exc))
            return

        resolver = lambda candidate: key if candidate == key_id else None
        if not action_is_authorized(receipt, resolver, action):
            decision = receipt["payload"]["decision"]
            QMessageBox.warning(
                self,
                "Verified export not authorized",
                "No artifact was written.\n\n"
                f"Decision: {decision['outcome']}\n"
                f"Reason: {', '.join(decision['reason_codes'])}\n\n"
                f"A metadata-only receipt was saved to:\n{receipt_path}",
            )
            return

        try:
            if is_report:
                self._save_report(path)
                message = f"Verified report exported to {path}"
            else:
                ok, message = build_dashboard(
                    self.manager.df,
                    path,
                    title=f"{APP_NAME} dashboard",
                    subtitle=os.path.basename(self.manager.source or "in-memory dataset"),
                )
                if not ok:
                    raise ValueError(message)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Verified export failed", str(exc))
            return
        self.statusBar().showMessage(message, 8000)
        QMessageBox.information(
            self,
            "Verified export complete",
            f"{message}\n\nMetadata-only trust receipt:\n{receipt_path}\n\n"
            "Keep the signing key outside source control; the receipt contains no raw dataset values.",
        )

    def _log_result(self, title: str, frame) -> None:
        self.analysis_log = [(t, f) for t, f in self.analysis_log if t != title]
        self.analysis_log.append((title, frame))
        self.analysis_log = self.analysis_log[-12:]

    # ------------------------------------------------------------------ misc
    def undo(self) -> None:
        label = self.manager.undo()
        if label:
            self.refresh_all()
            self.statusBar().showMessage(f"Undid: {label}", 5000)

    def redo(self) -> None:
        label = self.manager.redo()
        if label:
            self.refresh_all()
            self.statusBar().showMessage(f"Redid: {label}", 5000)

    def toggle_theme(self) -> None:
        self.dark = not self.dark
        self.settings.setValue("dark", self.dark)
        self.apply_theme()
        self.viz_tab.apply_theme(self.dark)
        self.timeseries_tab.apply_theme(self.dark)
        self.statusBar().showMessage(f"{'Dark' if self.dark else 'Light'} theme applied", 4000)

    def apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet(self.dark))

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME} {APP_VERSION}</h2><p>{APP_TAGLINE}</p>"
            f"<p>Import CSV, Excel, JSON, Parquet and SQLite data, clean and reshape it, run "
            f"statistical tests, train machine learning models, build charts and export "
            f"shareable HTML reports.</p>"
            f"<p>&copy; {APP_PUBLISHER} &middot; <a href='{APP_URL}'>{APP_URL}</a></p>",
        )

    def _require_data(self) -> bool:
        if self.manager.loaded:
            return True
        QMessageBox.information(self, "No dataset", "Import a dataset first.")
        return False

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        if not self.recent:
            empty = QAction("No recent files", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)
            return
        for path in self.recent:
            act = QAction(os.path.basename(path), self)
            act.setStatusTip(path)
            act.triggered.connect(lambda _=False, p=path: self._load_path(p))
            self.recent_menu.addAction(act)

    def refresh_all(self) -> None:
        for tab in (
            self.overview_tab, self.data_tab, self.transform_tab, self.analysis_tab,
            self.viz_tab, self.ml_tab, self.sql_tab, self.timeseries_tab, self.dashboard_tab,
            self.trust_center_tab,
        ):
            tab.refresh()
        self.act_undo.setEnabled(self.manager.can_undo)
        self.act_redo.setEnabled(self.manager.can_redo)
        if self.manager.loaded:
            source = self.manager.source or "in-memory dataset"
            self.status_dataset.setText(f"{os.path.basename(source)}")
            self.status_shape.setText(
                f"{len(self.manager.df):,} rows × {self.manager.df.shape[1]} columns · "
                f"{self.manager.memory_usage_mb():.2f} MB"
            )
        else:
            self.status_dataset.setText("No dataset loaded — use File ▸ Import data")
            self.status_shape.setText("")
