from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QFileDialog, QMessageBox, QHBoxLayout)
from core.report_generator import ReportGenerator
import os

class ReportTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.report_gen = ReportGenerator(data_manager)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Report Generation & Export:"))
        
        self.info_label = QLabel("Generate a professional PDF report including statistical summaries.")
        self.info_label.setWordWrap(True)
        self.layout.addWidget(self.info_label)

        self.btn_pdf = QPushButton("Export Analysis to PDF Report")
        self.btn_pdf.setMinimumHeight(50)
        self.btn_pdf.setStyleSheet("background-color: #2E8B57; color: white; font-weight: bold;")
        self.btn_pdf.clicked.connect(self.export_pdf)
        self.layout.addWidget(self.btn_pdf)

        self.layout.addStretch()

    def export_pdf(self):
        if self.data_manager.df is None:
            QMessageBox.warning(self, "Warning", "No data available to report.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "DataSense_Report.pdf", "PDF Files (*.pdf)")
        
        if file_path:
            # Optionally capture current chart from viz_tab if possible
            # For now, we generate summary report
            success, message = self.report_gen.generate_pdf(file_path)
            if success:
                QMessageBox.information(self, "Success", "PDF Report saved successfully!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to generate report: {message}")
