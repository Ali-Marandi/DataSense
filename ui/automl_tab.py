from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QMessageBox, QTextEdit)
from core.automl import AutoML

class AutoMLTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.automl = None
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("AutoML - Predictive Analytics:"))
        
        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(QLabel("Select Target Column:"))
        self.target_selector = QComboBox()
        self.h_layout.addWidget(self.target_selector)
        
        self.btn_refresh = QPushButton("Refresh Columns")
        self.btn_refresh.clicked.connect(self.update_columns)
        self.h_layout.addWidget(self.btn_refresh)
        
        self.layout.addLayout(self.h_layout)

        self.btn_train = QPushButton("Train Best Model (Auto)")
        self.btn_train.setMinimumHeight(45)
        self.btn_train.setStyleSheet("background-color: #008080; color: white; font-weight: bold;")
        self.btn_train.clicked.connect(self.train_model)
        self.layout.addWidget(self.btn_train)

        self.result_log = QTextEdit()
        self.result_log.setReadOnly(True)
        self.layout.addWidget(self.result_log)

    def update_columns(self):
        cols = self.data_manager.get_columns()
        self.target_selector.clear()
        self.target_selector.addItems(cols)

    def train_model(self):
        df = self.data_manager.df
        if df is None:
            QMessageBox.warning(self, "Warning", "Please load data first.")
            return

        target = self.target_selector.currentText()
        if not target:
            QMessageBox.warning(self, "Warning", "Please select a target column.")
            return

        self.result_log.append(f"Starting AutoML training for target: {target}...")
        self.automl = AutoML(df)
        success, message = self.automl.train_best_model(target)
        
        if success:
            self.result_log.append(f"Success: {message}")
            QMessageBox.information(self, "AutoML", message)
        else:
            self.result_log.append(f"Error: {message}")
            QMessageBox.critical(self, "Error", f"Training failed: {message}")
