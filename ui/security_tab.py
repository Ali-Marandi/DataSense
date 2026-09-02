from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QLabel, QLineEdit, QMessageBox, QListWidget,
    QTableWidget, QTableWidgetItem, QGroupBox,
)

from core.security import DataSecurity
from core.model_registry import ModelRegistry


class SecurityTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.security = DataSecurity()
        self.registry = ModelRegistry()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)

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

        self.layout.addSpacing(16)
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

        registry_box = QGroupBox("Model Registry")
        registry_layout = QVBoxLayout(registry_box)
        registry_controls = QHBoxLayout()
        self.registry_filter = QComboBox()
        self.registry_filter.addItems(["all", "candidate", "approved", "retired"])
        self.registry_filter.currentTextChanged.connect(self.refresh_registry)
        registry_controls.addWidget(self.registry_filter)
        self.btn_refresh_registry = QPushButton("Refresh Registry")
        self.btn_refresh_registry.clicked.connect(self.refresh_registry)
        registry_controls.addWidget(self.btn_refresh_registry)
        self.btn_approve = QPushButton("Approve Selected")
        self.btn_approve.clicked.connect(self.approve_selected_model)
        registry_controls.addWidget(self.btn_approve)
        registry_layout.addLayout(registry_controls)
        self.registry_table = QTableWidget(0, 7)
        self.registry_table.setHorizontalHeaderLabels([
            "Name", "Version", "Task", "Target", "Status", "Dataset fingerprint", "Artifact SHA-256"
        ])
        self.registry_table.setAlternatingRowColors(True)
        registry_layout.addWidget(self.registry_table)
        self.layout.addWidget(registry_box)

    def _refresh_main_window(self) -> None:
        window = self.window()
        if hasattr(window, "refresh_all"):
            window.refresh_all()

    def update_columns(self):
        cols = self.data_manager.get_columns()
        current = self.col_selector.currentText()
        self.col_selector.clear()
        self.col_selector.addItems(cols)
        if current in cols:
            self.col_selector.setCurrentText(current)

    def encrypt_col(self):
        col = self.col_selector.currentText()
        if not col:
            return
        df, error = self.security.encrypt_column(self.data_manager.df, col)
        if error:
            QMessageBox.critical(self, "Error", error)
            return
        self.data_manager.set_frame(df, f"Encrypted column: {col}")
        QMessageBox.information(self, "Success", f"Column {col} encrypted.")
        self._refresh_main_window()

    def decrypt_col(self):
        col = self.col_selector.currentText()
        if not col:
            return
        df, error = self.security.decrypt_column(self.data_manager.df, col)
        if error:
            QMessageBox.critical(self, "Error", error)
            return
        self.data_manager.set_frame(df, f"Decrypted column: {col}")
        QMessageBox.information(self, "Success", f"Column {col} decrypted.")
        self._refresh_main_window()

    def save_ver(self):
        name = self.version_input.text().strip()
        if not name:
            return
        success, message = self.data_manager.save_version(name)
        if success:
            names = [self.version_list.item(i).text() for i in range(self.version_list.count())]
            if name not in names:
                self.version_list.addItem(name)
            self.version_input.clear()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Warning", message)

    def load_ver(self):
        item = self.version_list.currentItem()
        if not item:
            return
        name = item.text()
        success, message = self.data_manager.load_version(name)
        if success:
            QMessageBox.information(self, "Success", message)
            self._refresh_main_window()
        else:
            QMessageBox.warning(self, "Warning", message)

    def refresh_registry(self):
        try:
            self.registry.load()
        except Exception as exc:
            QMessageBox.warning(self, "Registry", str(exc))
            return
        status = self.registry_filter.currentText()
        rows = self.registry.records if status == "all" else [r for r in self.registry.records if r.status == status]
        self.registry_table.setRowCount(len(rows))
        for row_index, record in enumerate(rows):
            values = [record.name, record.version, record.task, record.target, record.status, record.dataset_fingerprint[:16], record.artifact_sha256[:16]]
            for column_index, value in enumerate(values):
                self.registry_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        self.registry_table.resizeColumnsToContents()

    def approve_selected_model(self):
        row = self.registry_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Registry", "Select a model first.")
            return
        name = self.registry_table.item(row, 0).text()
        version = self.registry_table.item(row, 1).text()
        try:
            record = self.registry.approve(name, version)
            if not self.registry.verify_artifact(record):
                QMessageBox.critical(self, "Registry", "Artifact integrity verification failed.")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Registry", str(exc))
            return
        self.refresh_registry()
        QMessageBox.information(self, "Registry", f"{name}:{version} approved.")
