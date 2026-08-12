"""Data workspace: preview, KPI overview and per-column quality profile."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.data_manager import DataManager
from .widgets.dataframe_model import DataFrameModel


class KpiCard(QLabel):
    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self.setProperty("role", "kpi")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.set_value("—")

    def set_value(self, value: str) -> None:
        self.setText(
            f"<span style='font-size:11px;letter-spacing:.08em;text-transform:uppercase;'>"
            f"{self._title}</span><br><b style='font-size:20px;'>{value}</b>"
        )


class DataTab(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, manager: DataManager) -> None:
        super().__init__()
        self.manager = manager
        self.preview_model = DataFrameModel()
        self.profile_model = DataFrameModel()
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.cards = {
            key: KpiCard(label)
            for key, label in (
                ("rows", "Rows"),
                ("cols", "Columns"),
                ("numeric", "Numeric columns"),
                ("missing", "Missing cells"),
                ("dupes", "Duplicate rows"),
                ("memory", "Memory"),
            )
        }
        for card in self.cards.values():
            kpis.addWidget(card)
        root.addLayout(kpis)

        controls = QGroupBox("Preview controls")
        grid = QGridLayout(controls)
        grid.addWidget(QLabel("Rows to preview"), 0, 0)
        self.row_spin = QSpinBox()
        self.row_spin.setRange(10, 100000)
        self.row_spin.setValue(500)
        self.row_spin.setSingleStep(50)
        self.row_spin.valueChanged.connect(self.refresh)
        grid.addWidget(self.row_spin, 0, 1)
        grid.addWidget(QLabel("Filter expression (pandas query)"), 0, 2)
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText('e.g. price > 100 and city == "Tehran"')
        self.query_edit.returnPressed.connect(self._apply_query)
        grid.addWidget(self.query_edit, 0, 3)
        apply_btn = QPushButton("Apply filter")
        apply_btn.setProperty("accent", True)
        apply_btn.clicked.connect(self._apply_query)
        grid.addWidget(apply_btn, 0, 4)
        grid.setColumnStretch(3, 1)
        root.addWidget(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)
        preview_box = QGroupBox("Dataset preview")
        preview_layout = QVBoxLayout(preview_box)
        self.preview_view = self._table(self.preview_model)
        preview_layout.addWidget(self.preview_view)
        splitter.addWidget(preview_box)

        profile_box = QGroupBox("Column quality profile")
        profile_layout = QVBoxLayout(profile_box)
        self.profile_view = self._table(self.profile_model)
        profile_layout.addWidget(self.profile_view)
        splitter.addWidget(profile_box)
        splitter.setSizes([520, 300])
        root.addWidget(splitter, 1)

    @staticmethod
    def _table(model) -> QTableView:
        view = QTableView()
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(False)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        view.horizontalHeader().setDefaultSectionSize(150)
        view.verticalHeader().setDefaultSectionSize(26)
        return view

    def _apply_query(self) -> None:
        expression = self.query_edit.text().strip()
        if not expression or not self.manager.loaded:
            return
        ok, message = self.manager.query(expression)
        self.window().statusBar().showMessage(message, 6000)
        if ok:
            self.dataChanged.emit()

    def refresh(self) -> None:
        if not self.manager.loaded:
            self.preview_model.set_frame(None)
            self.profile_model.set_frame(None)
            for card in self.cards.values():
                card.set_value("—")
            return
        df = self.manager.df
        self.preview_model.set_frame(df.head(self.row_spin.value()))
        self.profile_model.set_frame(self.manager.profile())
        self.cards["rows"].set_value(f"{len(df):,}")
        self.cards["cols"].set_value(str(df.shape[1]))
        self.cards["numeric"].set_value(str(len(self.manager.numeric_columns)))
        self.cards["missing"].set_value(f"{int(df.isna().sum().sum()):,}")
        self.cards["dupes"].set_value(f"{int(df.duplicated().sum()):,}")
        self.cards["memory"].set_value(f"{self.manager.memory_usage_mb():.2f} MB")
