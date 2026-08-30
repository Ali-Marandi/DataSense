"""Machine learning workspace with background training and explicit split semantics."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import ml
from core.data_manager import DataManager
from .widgets.dataframe_model import DataFrameModel

TASKS = ["Regression", "Classification", "Clustering (K-Means)", "PCA"]


class TrainWorker(QThread):
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, job) -> None:
        super().__init__()
        self._job = job

    def run(self) -> None:  # pragma: no cover - background thread
        try:
            self.finished_ok.emit(self._job())
        except Exception as exc:
            self.failed.emit(str(exc))


class MLTab(QWidget):
    resultReady = pyqtSignal(str, object)

    def __init__(self, manager: DataManager) -> None:
        super().__init__()
        self.manager = manager
        self.model = DataFrameModel()
        self.worker: TrainWorker | None = None
        self.last_result: ml.ModelResult | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        config = QGroupBox("Model configuration")
        grid = QGridLayout(config)
        grid.addWidget(QLabel("Task"), 0, 0)
        self.task_combo = QComboBox()
        self.task_combo.addItems(TASKS)
        self.task_combo.currentTextChanged.connect(self._sync)
        grid.addWidget(self.task_combo, 0, 1)
        grid.addWidget(QLabel("Algorithm"), 0, 2)
        self.algo_combo = QComboBox()
        grid.addWidget(self.algo_combo, 0, 3)
        grid.addWidget(QLabel("Target"), 0, 4)
        self.target_combo = QComboBox()
        grid.addWidget(self.target_combo, 0, 5)
        grid.addWidget(QLabel("Test size"), 1, 0)
        self.test_size = QDoubleSpinBox()
        self.test_size.setRange(0.05, 0.5)
        self.test_size.setSingleStep(0.05)
        self.test_size.setValue(0.2)
        grid.addWidget(self.test_size, 1, 1)
        grid.addWidget(QLabel("Time column (optional)"), 1, 2)
        self.time_combo = QComboBox()
        self.time_combo.addItem("Random split")
        grid.addWidget(self.time_combo, 1, 3)
        grid.addWidget(QLabel("Clusters / components"), 1, 4)
        self.k_spin = QSpinBox()
        self.k_spin.setRange(2, 20)
        self.k_spin.setValue(3)
        grid.addWidget(self.k_spin, 1, 5)
        self.train_btn = QPushButton("Train model")
        self.train_btn.setProperty("accent", True)
        self.train_btn.clicked.connect(self.train)
        grid.addWidget(self.train_btn, 2, 5)
        grid.setColumnStretch(3, 1)
        root.addWidget(config)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        features_box = QGroupBox("Features (multi-select)")
        features_layout = QVBoxLayout(features_box)
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        features_layout.addWidget(self.feature_list)
        splitter.addWidget(features_box)

        right = QSplitter(Qt.Orientation.Vertical)
        metrics_box = QGroupBox("Metrics & evaluation notes")
        metrics_layout = QVBoxLayout(metrics_box)
        self.metrics_view = QTextEdit()
        self.metrics_view.setReadOnly(True)
        self.metrics_view.setPlaceholderText("Train a model to see evaluation metrics.")
        metrics_layout.addWidget(self.metrics_view)
        right.addWidget(metrics_box)

        table_box = QGroupBox("Model detail")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(160)
        table_layout.addWidget(self.table)
        self.append_btn = QPushButton("Append predictions / clusters to dataset")
        self.append_btn.clicked.connect(self._append_predictions)
        table_layout.addWidget(self.append_btn)
        right.addWidget(table_box)
        right.setSizes([240, 460])
        splitter.addWidget(right)
        splitter.setSizes([300, 860])
        root.addWidget(splitter, 1)
        self._sync()

    def _sync(self) -> None:
        task = self.task_combo.currentText()
        self.algo_combo.clear()
        if task == "Regression":
            self.algo_combo.addItems(list(ml.REGRESSORS))
        elif task == "Classification":
            self.algo_combo.addItems(list(ml.CLASSIFIERS))
        else:
            self.algo_combo.addItem("K-Means" if "Clustering" in task else "PCA")
        supervised = task in {"Regression", "Classification"}
        self.target_combo.setEnabled(supervised)
        self.test_size.setEnabled(supervised)
        self.time_combo.setEnabled(supervised)
        self.k_spin.setEnabled(not supervised)

    def _features(self) -> list[str]:
        return [item.text() for item in self.feature_list.selectedItems()]

    def train(self) -> None:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        features = self._features()
        if not features:
            QMessageBox.information(self, "No features", "Select at least one feature column.")
            return
        df = self.manager.df
        task = self.task_combo.currentText()
        target = self.target_combo.currentText()
        algo = self.algo_combo.currentText()
        k = self.k_spin.value()
        size = self.test_size.value()
        features = [f for f in features if f != target]
        time_column = self.time_combo.currentText()
        time_column = time_column if time_column in df.columns else None
        if task in {"Regression", "Classification"} and not features:
            QMessageBox.information(self, "No features", "The target cannot be the only feature.")
            return

        if task == "Regression":
            job = lambda: ml.train_regression(df, target, features, algo, size, time_column)
        elif task == "Classification":
            job = lambda: ml.train_classification(df, target, features, algo, size, time_column)
        elif task.startswith("Clustering"):
            job = lambda: ml.run_clustering(df, features, k)
        else:
            job = lambda: ml.run_pca(df, features, k)

        self.train_btn.setEnabled(False)
        self.progress.show()
        self.worker = TrainWorker(job)
        self.worker.finished_ok.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.finished.connect(self._on_done)
        self.worker.start()

    def _on_success(self, result: ml.ModelResult) -> None:
        self.last_result = result
        self.model.set_frame(result.table)
        rows = "".join(
            f"<tr><td style='padding:3px 14px 3px 0;'>{k}</td><td><b>{v}</b></td></tr>"
            for k, v in result.metrics.items()
        )
        note = f"<p>{result.note}</p>" if result.note else ""
        self.metrics_view.setHtml(f"<h3>{result.title}</h3><table>{rows}</table>{note}")
        self.resultReady.emit(result.title, result.table)
        self.window().statusBar().showMessage(f"{result.title} trained", 6000)

    def _on_failure(self, message: str) -> None:
        QMessageBox.warning(self, "Training failed", message)

    def _on_done(self) -> None:
        self.progress.hide()
        self.train_btn.setEnabled(True)

    def _append_predictions(self) -> None:
        if self.last_result is None or self.last_result.predictions is None:
            QMessageBox.information(self, "Nothing to append", "Train a model first.")
            return
        predictions = self.last_result.predictions
        prediction_index = self.last_result.metadata.get("prediction_index")
        if isinstance(prediction_index, list) and len(prediction_index) == len(predictions):
            merged = self.manager.df.reset_index(drop=True).copy()
            for column in predictions.columns:
                aligned = pd.Series(index=merged.index, dtype=predictions[column].dtype)
                aligned.loc[prediction_index] = predictions[column].to_numpy()
                output_name = column if column not in merged.columns else f"{column} (model)"
                merged[output_name] = aligned
        elif len(predictions) == len(self.manager.df):
            merged = pd.concat([self.manager.df.reset_index(drop=True), predictions.reset_index(drop=True)], axis=1)
            merged = merged.loc[:, ~merged.columns.duplicated()]
        else:
            QMessageBox.information(
                self,
                "Row mismatch",
                "Predictions cover a subset of complete rows. Retrain after reviewing missing-value handling, or use the alignment metadata generated by time-aware evaluation.",
            )
            return
        self.manager.set_frame(merged, "Appended model output")
        self.window().statusBar().showMessage("Model output appended to the dataset", 6000)

    def refresh(self) -> None:
        columns = self.manager.columns
        numeric = self.manager.numeric_columns
        selected = set(self._features())
        self.feature_list.clear()
        self.feature_list.addItems(columns)
        for index in range(self.feature_list.count()):
            item = self.feature_list.item(index)
            if item.text() in selected:
                item.setSelected(True)
        current = self.target_combo.currentText()
        self.target_combo.clear()
        self.target_combo.addItems(columns)
        if current in columns:
            self.target_combo.setCurrentText(current)
        current_time = self.time_combo.currentText()
        self.time_combo.clear()
        self.time_combo.addItem("Random split")
        self.time_combo.addItems([c for c in self.manager.datetime_columns if c != self.target_combo.currentText()])
        if current_time in self.manager.columns:
            self.time_combo.setCurrentText(current_time)
        self.k_spin.setMaximum(max(2, min(20, len(numeric) or 20)))
