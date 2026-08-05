import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QStatusBar, QTabWidget)
from PyQt6.QtCore import Qt
from core.data_manager import DataManager
from ui.visualization_tab import VisualizationTab
from ui.analysis_tab import AnalysisTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DataSense - Advanced Data Analysis Platform")
        self.resize(1100, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.header_label = QLabel("DataSense Platform")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #008080; margin: 15px;")
        self.main_layout.addWidget(self.header_label)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Data Tab
        self.data_tab = QWidget()
        self.data_layout = QVBoxLayout(self.data_tab)
        
        self.btn_load = QPushButton("Load Data File (CSV/Excel/JSON)")
        self.btn_load.setMinimumHeight(40)
        self.btn_load.clicked.connect(self.load_file)
        self.data_layout.addWidget(self.btn_load)

        self.table = QTableWidget()
        self.data_layout.addWidget(self.table)
        
        self.tabs.addTab(self.data_tab, "Data Management")

        # Analysis Tab
        self.analysis_tab = AnalysisTab(self.data_manager)
        self.tabs.addTab(self.analysis_tab, "Statistical Analysis")

        # Visualization Tab
        self.viz_tab = VisualizationTab(self.data_manager)
        self.tabs.addTab(self.viz_tab, "Interactive Visualization")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Welcome to DataSense")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", 
                                                  "Data Files (*.csv *.xlsx *.xls *.json)")
        if file_path:
            success, message = self.data_manager.load_data(file_path)
            if success:
                self.status_bar.showMessage(f"Successfully loaded: {file_path}")
                self.update_table()
                self.viz_tab.update_columns()
            else:
                self.status_bar.showMessage(f"Error loading file: {message}")

    def update_table(self):
        df = self.data_manager.df
        if df is not None:
            display_rows = min(len(df), 100)
            self.table.setRowCount(display_rows)
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(df.columns)

            for i in range(display_rows):
                for j in range(len(df.columns)):
                    self.table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))
            self.table.resizeColumnsToContents()
