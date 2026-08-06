"""Preparation workspace: cleaning, typing, scaling, aggregation."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.data_manager import DataManager
from .widgets.dataframe_model import DataFrameModel

FILL_STRATEGIES = ["mean", "median", "mode", "forward", "backward", "zero", "constant"]
AGG_FUNCS = ["mean", "sum", "count", "min", "max", "median", "std"]


class TransformTab(QWidget):
    dataChanged = pyqtSignal()

    def __init__(self, manager: DataManager) -> None:
        super().__init__()
        self.manager = manager
        self.result_model = DataFrameModel()
        self._build()

    # -------------------------------------------------------------------- ui
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(12)
        panel_layout.addWidget(self._columns_box())
        panel_layout.addWidget(self._missing_box())
        panel_layout.addWidget(self._structure_box())
        panel_layout.addWidget(self._feature_box())
        panel_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(400)
        splitter.addWidget(scroll)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._aggregate_box())
        result_box = QGroupBox("Result preview")
        result_layout = QVBoxLayout(result_box)
        self.result_view = QTableView()
        self.result_view.setModel(self.result_model)
        self.result_view.setAlternatingRowColors(True)
        self.result_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.result_view.horizontalHeader().setDefaultSectionSize(150)
        result_layout.addWidget(self.result_view)
        self.promote_btn = QPushButton("Replace active dataset with this result")
        self.promote_btn.clicked.connect(self._promote_result)
        result_layout.addWidget(self.promote_btn)
        right_layout.addWidget(result_box, 1)
        splitter.addWidget(right)
        splitter.setSizes([440, 720])
        root.addWidget(splitter)

    def _columns_box(self) -> QGroupBox:
        box = QGroupBox("Columns")
        layout = QVBoxLayout(box)
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.column_list.setMinimumHeight(150)
        layout.addWidget(QLabel("Select one or more columns to operate on."))
        layout.addWidget(self.column_list)
        buttons = QHBoxLayout()
        drop_btn = QPushButton("Drop selected")
        drop_btn.setProperty("danger", True)
        drop_btn.clicked.connect(self._drop_columns)
        buttons.addWidget(drop_btn)
        rename_btn = QPushButton("Rename first")
        rename_btn.clicked.connect(self._rename_column)
        buttons.addWidget(rename_btn)
        layout.addLayout(buttons)
        return box

    def _missing_box(self) -> QGroupBox:
        box = QGroupBox("Missing values & duplicates")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("Fill strategy"), 0, 0)
        self.fill_strategy = QComboBox()
        self.fill_strategy.addItems(FILL_STRATEGIES)
        grid.addWidget(self.fill_strategy, 0, 1)
        self.fill_value = QLineEdit()
        self.fill_value.setPlaceholderText("constant value")
        grid.addWidget(self.fill_value, 0, 2)
        fill_btn = QPushButton("Fill selected columns")
        fill_btn.setProperty("accent", True)
        fill_btn.clicked.connect(self._fill_missing)
        grid.addWidget(fill_btn, 1, 0, 1, 3)
        drop_rows = QPushButton("Drop rows containing missing values")
        drop_rows.clicked.connect(self._drop_missing_rows)
        grid.addWidget(drop_rows, 2, 0, 1, 3)
        dedupe = QPushButton("Remove duplicate rows")
        dedupe.clicked.connect(self._dedupe)
        grid.addWidget(dedupe, 3, 0, 1, 3)
        return box

    def _structure_box(self) -> QGroupBox:
        box = QGroupBox("Types, scaling & outliers")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("Convert type"), 0, 0)
        self.cast_type = QComboBox()
        self.cast_type.addItems(["numeric", "datetime", "category", "text"])
        grid.addWidget(self.cast_type, 0, 1)
        cast_btn = QPushButton("Convert selected")
        cast_btn.clicked.connect(self._cast)
        grid.addWidget(cast_btn, 0, 2)

        grid.addWidget(QLabel("Scaling"), 1, 0)
        self.scale_method = QComboBox()
        self.scale_method.addItems(["standard", "minmax"])
        grid.addWidget(self.scale_method, 1, 1)
        scale_btn = QPushButton("Scale selected")
        scale_btn.clicked.connect(self._scale)
        grid.addWidget(scale_btn, 1, 2)

        grid.addWidget(QLabel("Outlier IQR factor"), 2, 0)
        self.iqr_factor = QDoubleSpinBox()
        self.iqr_factor.setRange(0.5, 5.0)
        self.iqr_factor.setSingleStep(0.1)
        self.iqr_factor.setValue(1.5)
        grid.addWidget(self.iqr_factor, 2, 1)
        outlier_btn = QPushButton("Remove outliers")
        outlier_btn.clicked.connect(self._remove_outliers)
        grid.addWidget(outlier_btn, 2, 2)
        return box

    def _feature_box(self) -> QGroupBox:
        box = QGroupBox("Computed column")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("New column name"), 0, 0)
        self.new_name = QLineEdit()
        grid.addWidget(self.new_name, 0, 1)
        grid.addWidget(QLabel("Expression"), 1, 0)
        self.new_expression = QLineEdit()
        self.new_expression.setPlaceholderText("e.g. revenue / units")
        grid.addWidget(self.new_expression, 1, 1)
        add_btn = QPushButton("Create column")
        add_btn.setProperty("accent", True)
        add_btn.clicked.connect(self._add_column)
        grid.addWidget(add_btn, 2, 0, 1, 2)
        return box

    def _aggregate_box(self) -> QGroupBox:
        box = QGroupBox("Group & pivot")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("Group by"), 0, 0)
        self.group_by = QComboBox()
        grid.addWidget(self.group_by, 0, 1)
        grid.addWidget(QLabel("Measure"), 0, 2)
        self.group_target = QComboBox()
        grid.addWidget(self.group_target, 0, 3)
        grid.addWidget(QLabel("Function"), 0, 4)
        self.group_func = QComboBox()
        self.group_func.addItems(AGG_FUNCS)
        grid.addWidget(self.group_func, 0, 5)
        group_btn = QPushButton("Aggregate")
        group_btn.setProperty("accent", True)
        group_btn.clicked.connect(self._aggregate)
        grid.addWidget(group_btn, 0, 6)

        grid.addWidget(QLabel("Pivot columns"), 1, 0)
        self.pivot_columns = QComboBox()
        grid.addWidget(self.pivot_columns, 1, 1)
        pivot_btn = QPushButton("Build pivot table")
        pivot_btn.clicked.connect(self._pivot)
        grid.addWidget(pivot_btn, 1, 2, 1, 5)
        return box

    # ------------------------------------------------------------- behaviour
    def _selected(self) -> list[str]:
        return [item.text() for item in self.column_list.selectedItems()]

    def _guard(self, need_columns: bool = True) -> bool:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return False
        if need_columns and not self._selected():
            QMessageBox.information(self, "No selection", "Select at least one column.")
            return False
        return True

    def _done(self, message: str) -> None:
        self.window().statusBar().showMessage(message, 6000)
        self.dataChanged.emit()

    def _drop_columns(self) -> None:
        if not self._guard():
            return
        self.manager.drop_columns(self._selected())
        self._done("Columns dropped")

    def _rename_column(self) -> None:
        if not self._guard():
            return
        from PyQt6.QtWidgets import QInputDialog

        old = self._selected()[0]
        new, ok = QInputDialog.getText(self, "Rename column", f"New name for '{old}'")
        if ok and new.strip():
            self.manager.rename_column(old, new.strip())
            self._done(f"Renamed to {new.strip()}")

    def _fill_missing(self) -> None:
        if not self._guard():
            return
        self.manager.fill_missing(
            self._selected(), self.fill_strategy.currentText(), self.fill_value.text()
        )
        self._done("Missing values filled")

    def _drop_missing_rows(self) -> None:
        if not self._guard(need_columns=False):
            return
        removed = self.manager.drop_missing(subset=self._selected() or None)
        self._done(f"{removed:,} rows removed")

    def _dedupe(self) -> None:
        if not self._guard(need_columns=False):
            return
        removed = self.manager.drop_duplicates(subset=self._selected() or None)
        self._done(f"{removed:,} duplicate rows removed")

    def _cast(self) -> None:
        if not self._guard():
            return
        for column in self._selected():
            ok, message = self.manager.cast_column(column, self.cast_type.currentText())
            if not ok:
                QMessageBox.warning(self, "Conversion failed", message)
                return
        self._done("Type conversion applied")

    def _scale(self) -> None:
        if not self._guard():
            return
        self.manager.scale_columns(self._selected(), self.scale_method.currentText())
        self._done("Columns scaled")

    def _remove_outliers(self) -> None:
        if not self._guard():
            return
        removed = self.manager.remove_outliers(self._selected(), self.iqr_factor.value())
        self._done(f"{removed:,} outlier rows removed")

    def _add_column(self) -> None:
        if not self._guard(need_columns=False):
            return
        name = self.new_name.text().strip()
        expression = self.new_expression.text().strip()
        if not name or not expression:
            QMessageBox.information(self, "Missing input", "Provide a name and an expression.")
            return
        ok, message = self.manager.add_computed_column(name, expression)
        if not ok:
            QMessageBox.warning(self, "Invalid expression", message)
            return
        self._done(message)

    def _aggregate(self) -> None:
        if not self._guard(need_columns=False):
            return
        try:
            frame = self.manager.group_aggregate(
                [self.group_by.currentText()],
                [self.group_target.currentText()],
                [self.group_func.currentText()],
            )
        except Exception as exc:
            QMessageBox.warning(self, "Aggregation failed", str(exc))
            return
        self.result_model.set_frame(frame)
        self.window().statusBar().showMessage(f"Aggregated into {len(frame):,} groups", 6000)

    def _pivot(self) -> None:
        if not self._guard(need_columns=False):
            return
        try:
            frame = self.manager.pivot(
                self.group_by.currentText(),
                self.pivot_columns.currentText(),
                self.group_target.currentText(),
                self.group_func.currentText(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Pivot failed", str(exc))
            return
        self.result_model.set_frame(frame)
        self.window().statusBar().showMessage("Pivot table built", 6000)

    def _promote_result(self) -> None:
        frame = self.result_model.frame
        if frame is None or frame.empty:
            QMessageBox.information(self, "Nothing to promote", "Build a result table first.")
            return
        self.manager.set_frame(frame, "Promoted aggregated result")
        self._done("Active dataset replaced with the result table")

    def refresh(self) -> None:
        selected = set(self._selected())
        self.column_list.clear()
        columns = self.manager.columns()
        self.column_list.addItems(columns)
        for index in range(self.column_list.count()):
            item = self.column_list.item(index)
            if item.text() in selected:
                item.setSelected(True)
        for combo, values in (
            (self.group_by, columns),
            (self.pivot_columns, columns),
            (self.group_target, self.manager.numeric_columns() or columns),
        ):
            current = combo.currentText()
            combo.clear()
            combo.addItems(values)
            if current in values:
                combo.setCurrentText(current)
