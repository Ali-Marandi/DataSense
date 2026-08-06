from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QMessageBox)
from core.streaming import RealTimeSimulator
import pandas as pd

class StreamingTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.simulator = None
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Real-time Data Streaming Simulator:"))
        
        self.btn_start = QPushButton("Start Real-time Stream")
        self.btn_start.clicked.connect(self.start_stream)
        self.layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("Stop Stream")
        self.btn_stop.clicked.connect(self.stop_stream)
        self.btn_stop.setEnabled(False)
        self.layout.addWidget(self.btn_stop)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

    def start_stream(self):
        if self.data_manager.df is None:
            QMessageBox.warning(self, "Warning", "Please load a base dataset first to get columns.")
            return
        
        cols = self.data_manager.df.columns.tolist()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(0)

        self.simulator = RealTimeSimulator(cols)
        self.simulator.data_received.connect(self.handle_data)
        self.simulator.start()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_stream(self):
        if self.simulator:
            self.simulator.stop()
            self.simulator.wait()
            self.simulator = None
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def handle_data(self, df):
        """افزودن داده‌های دریافتی جدید به جدول"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        for i, val in enumerate(df.iloc[0]):
            self.table.setItem(row, i, QTableWidgetItem(f"{val:.4f}"))
        
        # Optionally update data_manager.df with new data (appending)
        self.data_manager.df = pd.concat([self.data_manager.df, df], ignore_index=True)
        
        # Auto-scroll to bottom
        self.table.scrollToBottom()
        
        # Refresh other tabs periodically or after each data point
        if row % 5 == 0: # Every 5 rows
            if hasattr(self.parent().parent(), 'refresh_all'):
                self.parent().parent().refresh_all()
