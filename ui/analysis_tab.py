from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel)

class AnalysisTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.btn_analyze = QPushButton("Run Statistical Analysis")
        self.btn_analyze.clicked.connect(self.run_analysis)
        self.layout.addWidget(self.btn_analyze)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.layout.addWidget(self.result_area)

    def run_analysis(self):
        df = self.data_manager.df
        if df is not None:
            summary = df.describe().to_string()
            corr = df.corr(numeric_only=True).to_string()
            
            report = f"--- Statistical Summary ---\n\n{summary}\n\n"
            report += f"--- Correlation Matrix ---\n\n{corr}\n"
            
            self.result_area.setText(report)
        else:
            self.result_area.setText("No data loaded for analysis.")
