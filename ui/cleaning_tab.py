from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QCheckBox, 
                             QLabel, QMessageBox, QHBoxLayout)

class CleaningTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.layout.addWidget(QLabel("Smart Data Cleaning Options:"))

        self.cb_fill_na = QCheckBox("Auto-fill Missing Values (Mean for numbers, Mode for text)")
        self.cb_fill_na.setChecked(True)
        self.layout.addWidget(self.cb_fill_na)

        self.cb_drop_dup = QCheckBox("Remove Duplicate Rows")
        self.cb_drop_dup.setChecked(True)
        self.layout.addWidget(self.cb_drop_dup)

        self.btn_clean = QPushButton("Run Smart Cleaning")
        self.btn_clean.setMinimumHeight(40)
        self.btn_clean.clicked.connect(self.run_cleaning)
        self.layout.addWidget(self.btn_clean)

        self.layout.addStretch()

    def run_cleaning(self):
        fill_na = self.cb_fill_na.isChecked()
        drop_dup = self.cb_drop_dup.isChecked()

        success, message = self.data_manager.clean_data(fill_na, drop_dup)
        if success:
            QMessageBox.information(self, "Success", "Data cleaned successfully!")
            # Update table in main window
            if hasattr(self.parent().parent(), 'update_table'):
                self.parent().parent().update_table()
        else:
            QMessageBox.critical(self, "Error", f"Cleaning failed: {message}")
