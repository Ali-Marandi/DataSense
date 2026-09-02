from __future__ import annotations

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.report_generator import ReportGenerator


class ReportTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.report_gen = ReportGenerator(data_manager)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("Report Generation & Export:"))

        self.info_label = QLabel(
            "Generate a professional report with dataset summary, quality evidence, "
            "schema-drift status and reproducibility metadata."
        )
        self.info_label.setWordWrap(True)
        self.layout.addWidget(self.info_label)

        self.btn_pdf = QPushButton("Export Analysis to PDF Report")
        self.btn_pdf.setMinimumHeight(50)
        self.btn_pdf.clicked.connect(self.export_pdf)
        self.layout.addWidget(self.btn_pdf)

        self.btn_html = QPushButton("Export Evidence-Aware HTML Report")
        self.btn_html.setMinimumHeight(50)
        self.btn_html.clicked.connect(self.export_interactive_html)
        self.layout.addWidget(self.btn_html)
        self.layout.addStretch()

    def _validate_dataset(self) -> bool:
        if self.data_manager.df is None:
            QMessageBox.warning(self, "Warning", "No data available to report.")
            return False
        return True

    def export_pdf(self):
        if not self._validate_dataset():
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", "DataSense_Report.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        success, message = self.report_gen.generate_pdf(file_path)
        if success:
            QMessageBox.information(self, "Success", "PDF Report saved successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {message}")

    def export_interactive_html(self):
        if not self._validate_dataset():
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML Report", "DataSense_Report.html", "HTML Files (*.html)"
        )
        if not file_path:
            return

        try:
            from core.report import ReportBuilder
            import plotly.express as px

            report = ReportBuilder(
                title="DataSense Evidence-Aware Analysis Report",
                subtitle="Local analysis and governed evidence",
            )
            df = self.data_manager.df
            report.set_metadata(
                source=self.data_manager.source or "unknown",
                rows=int(len(df)),
                columns=int(len(df.columns)),
                dataset_memory_mb=round(self.data_manager.memory_usage_mb(), 3),
            )
            report.add_metrics(
                "Dataset Overview",
                {
                    "Rows": len(df),
                    "Columns": len(df.columns),
                    "Missing cells": int(df.isna().sum().sum()),
                    "Memory": f"{self.data_manager.memory_usage_mb():.2f} MB",
                },
            )

            governance = self.data_manager.governance_report
            gate = governance.gate_decision(self.data_manager.quality_gate_policy) if governance else None
            drift = self.data_manager.check_schema_drift()
            report.add_governance_snapshot(governance, gate=gate, schema_drift=drift)

            profile = self.data_manager.profile()
            if not profile.empty:
                report.add_table("Column Quality Profile", profile)

            numeric_cols = list(df.select_dtypes(include=["number"]).columns)
            if len(numeric_cols) >= 2:
                fig = px.scatter(
                    df,
                    x=numeric_cols[0],
                    y=numeric_cols[1],
                    title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
                )
                report.add_plotly_figure("Interactive Scatter Analysis", fig)

            report.add_text(
                "Evidence Boundary",
                "This report records analysis outputs and metadata. It does not claim model correctness, causal validity, certification, or measurement uncertainty. Quality-gate approval is a policy decision over the evidence available at export time.",
            )
            report.save(file_path)
            QMessageBox.information(self, "Success", "Evidence-aware HTML report saved successfully!")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to generate report: {exc}")
