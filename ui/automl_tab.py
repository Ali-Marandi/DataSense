from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from core.automl import AutoML


class AutoMLWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, runner: AutoML, target: str, test_size: float) -> None:
        super().__init__()
        self.runner = runner
        self.target = target
        self.test_size = test_size

    def run(self) -> None:  # pragma: no cover - background thread
        try:
            self.succeeded.emit(self.runner.run(self.target, test_size=self.test_size))
        except Exception as exc:
            self.failed.emit(str(exc))


class AutoMLTab(QWidget):
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.automl: AutoML | None = None
        self.worker: AutoMLWorker | None = None
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.addWidget(QLabel("AutoML — bounded model comparison with reproducible validation"))

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Target:"))
        self.target_selector = QComboBox()
        controls.addWidget(self.target_selector, 1)
        controls.addWidget(QLabel("Test size:"))
        self.test_size = QDoubleSpinBox()
        self.test_size.setRange(0.05, 0.5)
        self.test_size.setSingleStep(0.05)
        self.test_size.setValue(0.2)
        controls.addWidget(self.test_size)
        self.time_selector = QComboBox()
        self.time_selector.addItem("Random split")
        controls.addWidget(QLabel("Time-aware:"))
        controls.addWidget(self.time_selector, 1)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.update_columns)
        controls.addWidget(self.btn_refresh)
        root.addLayout(controls)

        self.btn_train = QPushButton("Compare models")
        self.btn_train.clicked.connect(self.train_model)
        self.btn_train.setMinimumHeight(42)
        root.addWidget(self.btn_train)

        self.table = QTableWidget(0, 0)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        root.addWidget(QLabel("Winner / evaluation notes"))
        self.result_log = QTextEdit()
        self.result_log.setReadOnly(True)
        root.addWidget(self.result_log)
        self.update_columns()

    def update_columns(self):
        cols = self.data_manager.get_columns()
        self.target_selector.clear()
        self.target_selector.addItems(cols)
        current_time = self.time_selector.currentText()
        self.time_selector.clear()
        self.time_selector.addItem("Random split")
        self.time_selector.addItems([c for c in getattr(self.data_manager, "datetime_columns", []) if c != self.target_selector.currentText()])
        if current_time in cols:
            self.time_selector.setCurrentText(current_time)

    def train_model(self):
        df = self.data_manager.df
        if df is None:
            QMessageBox.warning(self, "AutoML", "Please load data first.")
            return
        target = self.target_selector.currentText()
        if not target:
            QMessageBox.warning(self, "AutoML", "Please select a target column.")
            return
        time_column = self.time_selector.currentText()
        self.automl = AutoML(df, time_column=time_column if time_column in df.columns else None)
        self.result_log.setPlainText(f"Comparing bounded model families for '{target}'…")
        self.btn_train.setEnabled(False)
        self.worker = AutoMLWorker(self.automl, target, self.test_size.value())
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.finished.connect(lambda: self.btn_train.setEnabled(True))
        self.worker.start()

    def _on_success(self, result) -> None:
        columns = ["Model"]
        all_metrics: list[str] = []
        for candidate in result.candidates:
            for key in candidate.metrics:
                if key not in all_metrics:
                    all_metrics.append(key)
        columns.extend(all_metrics)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(result.candidates))
        for row, candidate in enumerate(result.candidates):
            values = [candidate.title]
            values.extend(candidate.metrics.get(key, "") for key in all_metrics)
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        metric = "R2 (test)" if result.task == "regression" else "F1 (weighted)"
        winner_score = result.best.metrics.get(metric)
        note = result.best.note
        self.result_log.setPlainText(
            f"Task: {result.task}\nTarget: {result.target}\n\n"
            f"Winner: {result.best.title}\n{metric}: {winner_score}\n\n{note}"
        )
        self.window().statusBar().showMessage(f"AutoML winner: {result.best.title}", 8000)

    def _on_failure(self, message: str) -> None:
        self.result_log.setPlainText(f"Training failed: {message}")
        QMessageBox.warning(self, "AutoML", message)
