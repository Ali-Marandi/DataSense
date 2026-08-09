"""Interactive dashboard workspace: build and preview shareable HTML dashboards."""
from __future__ import annotations

import os
import tempfile
import webbrowser

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.dashboard import build_dashboard
from core.insights import insights_frame, summary_metrics


class DashboardTab(QWidget):
    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        root.addWidget(QLabel(
            "Generate a self-contained interactive dashboard (Plotly) with KPIs, "
            "distributions, a correlation heatmap and automatic insights."
        ))

        bar = QHBoxLayout()
        self.title_edit = QLineEdit("DataSense dashboard")
        self.charts = QSpinBox()
        self.charts.setRange(1, 12)
        self.charts.setValue(6)
        self.preview_btn = QPushButton("Preview in browser")
        self.export_btn = QPushButton("Export HTML...")
        self.preview_btn.clicked.connect(self.preview)
        self.export_btn.clicked.connect(self.export)
        bar.addWidget(QLabel("Title:"))
        bar.addWidget(self.title_edit, 1)
        bar.addWidget(QLabel("Max charts:"))
        bar.addWidget(self.charts)
        bar.addWidget(self.preview_btn)
        bar.addWidget(self.export_btn)
        root.addLayout(bar)

        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        root.addWidget(self.summary, 1)

        self.status = QLabel("No dataset loaded.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def refresh(self) -> None:
        if not self.manager.loaded:
            self.summary.setPlainText("")
            self.status.setText("No dataset loaded.")
            return
        lines = [f"{k}: {v}" for k, v in summary_metrics(self.manager.df).items()]
        frame = insights_frame(self.manager.df)
        if not frame.empty:
            lines.append("")
            lines.append("Insights that will appear in the dashboard:")
            lines += [f"  [{r.severity}] {r.title}" for r in frame.itertuples()]
        self.summary.setPlainText("\n".join(lines))
        self.status.setText("Ready to build the dashboard.")

    def _build(self, path: str) -> bool:
        ok, message = build_dashboard(
            self.manager.df, path,
            title=self.title_edit.text().strip() or "DataSense dashboard",
            subtitle=os.path.basename(self.manager.source or "in-memory dataset"),
            max_charts=self.charts.value(),
        )
        self.status.setText(message)
        if not ok:
            QMessageBox.warning(self, "Dashboard", message)
        return ok

    def preview(self) -> None:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        path = os.path.join(tempfile.gettempdir(), "datasense-dashboard.html")
        if self._build(path):
            webbrowser.open(f"file://{path}")

    def export(self) -> None:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export dashboard", "datasense-dashboard.html", "HTML dashboard (*.html)"
        )
        if path:
            self._build(path)
