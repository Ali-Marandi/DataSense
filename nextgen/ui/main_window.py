from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.composition import Services
from core.data.model import DatasetProfile
from core.governance.contracts import QualityReport
from core.telemetry.events import TelemetryEvent
from ui.dashboard_panel import DashboardPanel
from ui.theme import DARK_STYLESHEET


class MainWindow(QMainWindow):
    """Desktop shell for the Explore → Validate → Deliver workflow.

    Widgets orchestrate services exposed by the composition root.  No PyQt widget
    evaluates a dataframe, calculates a quality rule, or constructs receipt content.
    """

    _PAGE_INDEX = {"Dashboard": 0, "Explore": 1, "Prepare & Validate": 2, "Deliver": 3}

    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
        self._last_receipt_path: Path | None = None
        self.setWindowTitle("DataSense Alpha — Trusted local analytics")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(DARK_STYLESHEET)
        self._build_ui()
        self._render_state()

    def _build_ui(self) -> None:
        self._build_toolbar()
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(self._navigation())
        self.pages = QStackedWidget()
        self.dashboard = DashboardPanel()
        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self._explore_page())
        self.pages.addWidget(self._validate_page())
        self.pages.addWidget(self._deliver_page())
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        status = QStatusBar()
        status.showMessage("Local-only mode · raw data remains on this device")
        self.setStatusBar(status)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Workspace actions")
        toolbar.setMovable(False)
        open_action = QAction("Open CSV", self)
        open_action.triggered.connect(self._open_csv)
        sample_action = QAction("Load sample", self)
        sample_action.triggered.connect(self._load_sample)
        check_action = QAction("Run checks", self)
        check_action.triggered.connect(self._run_quality_checks)
        export_action = QAction("Verified export", self)
        export_action.triggered.connect(self._export_verified)
        toolbar.addAction(open_action)
        toolbar.addAction(sample_action)
        toolbar.addSeparator()
        toolbar.addAction(check_action)
        toolbar.addAction(export_action)
        self.addToolBar(toolbar)

    def _navigation(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        title = QLabel("DataSense")
        title.setObjectName("navBrand")
        subtitle = QLabel("Trusted local analytics")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(22)
        self.nav_buttons: dict[str, QPushButton] = {}
        for label in self._PAGE_INDEX:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.clicked.connect(lambda _checked=False, value=label: self._navigate(value))
            layout.addWidget(button)
            self.nav_buttons[label] = button
        layout.addStretch()
        footer = QLabel("ALPHA BUILD\nNo raw dataset leaves this device.")
        footer.setObjectName("navFooter")
        footer.setWordWrap(True)
        layout.addWidget(footer)
        return panel

    def _navigate(self, label: str) -> None:
        self.pages.setCurrentIndex(self._PAGE_INDEX[label])
        for name, button in self.nav_buttons.items():
            button.setProperty("active", name == label)
            button.style().unpolish(button)
            button.style().polish(button)

    def _page_shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel(title)
        heading.setObjectName("pageHeading")
        text = QLabel(subtitle)
        text.setObjectName("muted")
        text.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(text)
        layout.addSpacing(8)
        return page, layout

    def _explore_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Explore",
            "Open a local CSV or use a safe sample. Profile results are computed on this device and shown as aggregate metadata.",
        )
        action_row = QHBoxLayout()
        import_button = QPushButton("Open local CSV")
        import_button.clicked.connect(self._open_csv)
        sample_button = QPushButton("Load sample operations data")
        sample_button.clicked.connect(self._load_sample)
        action_row.addWidget(import_button)
        action_row.addWidget(sample_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.dataset_status = QLabel()
        self.dataset_status.setObjectName("datasetStatus")
        self.dataset_status.setWordWrap(True)
        layout.addWidget(self.dataset_status)
        self.profile_view = QTextEdit()
        self.profile_view.setObjectName("profileView")
        self.profile_view.setReadOnly(True)
        self.profile_view.setMaximumHeight(138)
        layout.addWidget(self.profile_view)

        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        label = QLabel("LOCAL DATA PREVIEW")
        label.setObjectName("sectionTitle")
        preview_layout.addWidget(label)
        self.preview_table = QTableWidget(0, 0)
        self.preview_table.setObjectName("previewTable")
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_card, 1)
        return page

    def _validate_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Prepare & Validate",
            "Run the active local data contract. Critical and high-severity findings block verified delivery; advisory findings remain visible.",
        )
        button = QPushButton("Run quality checks")
        button.clicked.connect(self._run_quality_checks)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.quality_summary = QLabel("No checks have been run for the active dataset.")
        self.quality_summary.setObjectName("qualitySummary")
        self.quality_summary.setWordWrap(True)
        layout.addWidget(self.quality_summary)
        self.quality_table = QTableWidget(0, 5)
        self.quality_table.setObjectName("qualityTable")
        self.quality_table.setHorizontalHeaderLabels(["Rule", "Severity", "Status", "Violations", "Detail"])
        self.quality_table.verticalHeader().setVisible(False)
        self.quality_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quality_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quality_table.setAlternatingRowColors(True)
        self.quality_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.quality_table, 1)
        return page

    def _deliver_page(self) -> QWidget:
        page, layout = self._page_shell(
            "Deliver",
            "Create a verified HTML artifact only after the active contract passes. Every attempt produces a metadata-only, locally signed receipt.",
        )
        action_row = QHBoxLayout()
        export_button = QPushButton("Export verified HTML report")
        export_button.clicked.connect(self._export_verified)
        verify_button = QPushButton("Verify latest receipt")
        verify_button.clicked.connect(self._verify_latest_receipt)
        action_row.addWidget(export_button)
        action_row.addWidget(verify_button)
        action_row.addStretch()
        layout.addLayout(action_row)
        self.delivery_view = QTextEdit()
        self.delivery_view.setObjectName("deliveryView")
        self.delivery_view.setReadOnly(True)
        layout.addWidget(self.delivery_view, 1)
        return page

    def _open_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open local dataset",
            "",
            "Delimited files (*.csv *.tsv *.txt)",
        )
        if not path:
            return
        try:
            self._set_dataset(self.services.data.load_csv(path), Path(path).name)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def _load_sample(self) -> None:
        self._set_dataset(self.services.data.sample_dataset(), "DataSense sample operations dataset")

    def _set_dataset(self, frame: pd.DataFrame, label: str) -> None:
        self.services.state.frame = frame
        self.services.state.source_label = label
        self.services.state.quality_report = None
        self._last_receipt_path = None
        self._render_state()
        self.statusBar().showMessage(f"Loaded {label} locally · run validation before verified export")

    def _run_quality_checks(self) -> None:
        frame = self.services.state.frame
        if frame is None:
            QMessageBox.information(self, "No dataset", "Open data before running quality checks.")
            return
        report = self.services.state.contract.evaluate(frame)
        self.services.state.quality_report = report
        self._render_quality_report(report)
        self._render_state()
        self.services.telemetry.enqueue(
            TelemetryEvent(
                "quality_check_finished",
                {"rule_count_bucket": "1-5", "outcome": str(report.summary()["status"]), "app_version": "0.1.0"},
            ),
            consent=False,
        )
        self.statusBar().showMessage("Quality checks completed locally")

    def _export_verified(self) -> None:
        entitlement = self.services.feature_gate.decision("verified_export")
        if not entitlement.allowed:
            QMessageBox.information(
                self,
                "Verified export unavailable",
                f"This feature is currently unavailable: {entitlement.reason}.",
            )
            return
        frame = self.services.state.frame
        if frame is None:
            QMessageBox.information(self, "No dataset", "Open data before exporting.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save verified report",
            "datasense-verified-report.html",
            "HTML files (*.html)",
        )
        if not path:
            return
        profile = self.services.data.profile(frame)
        result = self.services.delivery.export_html(
            path,
            frame,
            profile,
            self.services.state.quality_report,
            signing_provider=self.services.signing_provider,
        )
        self._last_receipt_path = result.receipt_path
        if result.decision.approved:
            message = (
                f"Verified report saved:\n{result.artifact_path}\n\n"
                f"Signed metadata-only receipt:\n{result.receipt_path}\n\nReceipt SHA-256:\n{result.receipt_sha256}"
            )
        else:
            message = (
                f"Report blocked: {', '.join(result.decision.reason_codes)}\n\n"
                f"Signed decision receipt saved:\n{result.receipt_path}\n\nResolve the blocking findings and retry."
            )
        self.delivery_view.setPlainText(message)
        self.statusBar().showMessage("Verified export decision recorded locally")

    def _verify_latest_receipt(self) -> None:
        if self._last_receipt_path is None:
            QMessageBox.information(self, "No receipt", "Create or attempt a verified export before verifying a receipt.")
            return
        verified = self.services.delivery.verify_receipt(self._last_receipt_path, self.services.signing_provider)
        self.delivery_view.append("\nReceipt verification: " + ("VALID" if verified else "INVALID"))
        self.statusBar().showMessage("Receipt verification completed")

    def _render_state(self) -> None:
        frame = self.services.state.frame
        quality = self.services.state.quality_report
        if frame is None:
            self.dataset_status.setText("No dataset loaded")
            self.profile_view.setPlainText("Open a delimited file or load the safe sample to begin.")
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            self.dashboard.update_dashboard(None, quality, self.services.state.source_label)
            self._render_quality_report(quality)
            return
        profile = self.services.data.profile(frame)
        self.dataset_status.setText(f"{self.services.state.source_label}: {profile.rows:,} rows × {profile.columns} columns")
        self.profile_view.setPlainText("\n".join(f"{key}: {value}" for key, value in profile.summary().items()))
        self._populate_preview(frame)
        self.dashboard.update_dashboard(profile, quality, self.services.state.source_label)
        self._render_quality_report(quality)

    def _populate_preview(self, frame: pd.DataFrame, row_limit: int = 100) -> None:
        preview = frame.head(row_limit)
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels([str(column) for column in preview.columns])
        for row_index, (_, row) in enumerate(preview.iterrows()):
            for column_index, value in enumerate(row):
                self.preview_table.setItem(row_index, column_index, QTableWidgetItem("" if pd.isna(value) else str(value)))
        self.preview_table.resizeColumnsToContents()

    def _render_quality_report(self, report: QualityReport | None) -> None:
        if report is None:
            self.quality_summary.setText("No checks have been run for the active dataset.")
            self.quality_table.setRowCount(0)
            return
        summary = report.summary()
        self.quality_summary.setText(
            f"Status: {summary['status']} · {summary['rules']} rule(s) · "
            f"{summary['failed_rules']} failed · {summary['blocking_failures']} blocking"
        )
        self.quality_table.setRowCount(len(report.results))
        for row, result in enumerate(report.results):
            values = (
                f"{result.rule.column} / {result.rule.rule_type}",
                result.rule.severity,
                "PASS" if result.passed else "FAIL",
                str(result.violations),
                result.detail,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.quality_table.setItem(row, column, item)
        self.quality_table.resizeColumnsToContents()
