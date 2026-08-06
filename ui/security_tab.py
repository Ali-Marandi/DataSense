from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QLineEdit, QMessageBox, QListWidget)
from core.security import DataSecurity

class SecurityTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.security = DataSecurity()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # PII Encryption
        self.layout.addWidget(QLabel("PII Encryption (Security):"))
        self.pii_layout = QHBoxLayout()
        self.col_selector = QComboBox()
        self.pii_layout.addWidget(self.col_selector)
        
        self.btn_encrypt = QPushButton("Encrypt Column")
        self.btn_encrypt.clicked.connect(self.encrypt_col)
        self.pii_layout.addWidget(self.btn_encrypt)
        
        self.btn_decrypt = QPushButton("Decrypt Column")
        self.btn_decrypt.clicked.connect(self.decrypt_col)
        self.pii_layout.addWidget(self.btn_decrypt)
        
        self.layout.addLayout(self.pii_layout)
        
        self.btn_refresh = QPushButton("Refresh Columns")
        self.btn_refresh.clicked.connect(self.update_columns)
        self.layout.addWidget(self.btn_refresh)

        self.layout.addSpacing(20)

        # Data Versioning
        self.layout.addWidget(QLabel("Data Versioning:"))
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Enter version name...")
        self.layout.addWidget(self.version_input)
        
        self.btn_save_ver = QPushButton("Save Current Version")
        self.btn_save_ver.clicked.connect(self.save_ver)
        self.layout.addWidget(self.btn_save_ver)
        
        self.version_list = QListWidget()
        self.layout.addWidget(self.version_list)
        
        self.btn_load_ver = QPushButton("Restore Selected Version")
        self.btn_load_ver.clicked.connect(self.load_ver)
        self.layout.addWidget(self.btn_load_ver)

    def update_columns(self):
        cols = self.data_manager.get_columns()
        self.col_selector.clear()
        self.col_selector.addItems(cols)

    def encrypt_col(self):
        col = self.col_selector.currentText()
        if not col: return
        df, error = self.security.encrypt_column(self.data_manager.df, col)
        if error:
            QMessageBox.critical(self, "Error", error)
        else:
            QMessageBox.information(self, "Success", f"Column {col} encrypted.")
            if hasattr(self.parent().parent(), 'refresh_all'):
                self.parent().parent().refresh_all()

    def decrypt_col(self):
        col = self.col_selector.currentText()
        if not col: return
        df, error = self.security.decrypt_column(self.data_manager.df, col)
        if error:
            QMessageBox.critical(self, "Error", error)
        else:
            QMessageBox.information(self, "Success", f"Column {col} decrypted.")
            if hasattr(self.parent().parent(), 'refresh_all'):
                self.parent().parent().refresh_all()

    def save_ver(self):
        name = self.version_input.text().strip()
        if not name: return
        success, message = self.data_manager.save_version(name)
        if success:
            self.version_list.addItem(name)
            self.version_input.clear()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Warning", message)

    def load_ver(self):
        item = self.version_list.currentItem()
        if not item: return
        name = item.text()
        success, message = self.data_manager.load_version(name)
        if success:
            QMessageBox.information(self, "Success", message)
            if hasattr(self.parent().parent(), 'refresh_all'):
                self.parent().parent().refresh_all()
        else:
            QMessageBox.warning(self, "Warning", message)
