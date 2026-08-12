"""Statistics workspace: descriptives, correlation and hypothesis tests."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import statistics as st
from core.data_manager import DataManager
from .widgets.dataframe_model import DataFrameModel

TESTS = [
    "Descriptive statistics",
    "Correlation matrix",
    "Frequency table",
    "Normality (Shapiro-Wilk)",
    "Two-sample t-test",
    "Paired t-test",
    "One-way ANOVA",
    "Chi-square independence",
    "Linear regression (OLS)",
]


class AnalysisTab(QWidget):
    resultReady = pyqtSignal(str, object)

    def __init__(self, manager: DataManager) -> None:
        super().__init__()
        self.manager = manager
        self.model = DataFrameModel()
        self.last_title = ""
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        config = QGroupBox("Analysis configuration")
        grid = QGridLayout(config)
        grid.addWidget(QLabel("Analysis"), 0, 0)
        self.test_combo = QComboBox()
        self.test_combo.addItems(TESTS)
        self.test_combo.currentTextChanged.connect(self._sync_inputs)
        grid.addWidget(self.test_combo, 0, 1)

        grid.addWidget(QLabel("Primary variable"), 0, 2)
        self.primary = QComboBox()
        grid.addWidget(self.primary, 0, 3)
        grid.addWidget(QLabel("Secondary variable"), 0, 4)
        self.secondary = QComboBox()
        grid.addWidget(self.secondary, 0, 5)

        grid.addWidget(QLabel("Correlation method"), 1, 0)
        self.method = QComboBox()
        self.method.addItems(["pearson", "spearman", "kendall"])
        grid.addWidget(self.method, 1, 1)

        run = QPushButton("Run analysis")
        run.setProperty("accent", True)
        run.clicked.connect(self.run)
        grid.addWidget(run, 1, 5)
        grid.setColumnStretch(3, 1)
        root.addWidget(config)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        columns_box = QGroupBox("Variables (multi-select)")
        columns_layout = QVBoxLayout(columns_box)
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        columns_layout.addWidget(self.column_list)
        splitter.addWidget(columns_box)

        right = QSplitter(Qt.Orientation.Vertical)
        table_box = QGroupBox("Result table")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(150)
        table_layout.addWidget(self.table)
        right.addWidget(table_box)

        interp_box = QGroupBox("Interpretation")
        interp_layout = QVBoxLayout(interp_box)
        self.interpretation = QTextEdit()
        self.interpretation.setReadOnly(True)
        self.interpretation.setPlaceholderText(
            "Run an analysis to see the statistical interpretation here."
        )
        interp_layout.addWidget(self.interpretation)
        right.addWidget(interp_box)
        right.setSizes([460, 220])
        splitter.addWidget(right)
        splitter.setSizes([300, 860])
        root.addWidget(splitter, 1)
        self._sync_inputs()

    def _sync_inputs(self) -> None:
        test = self.test_combo.currentText()
        needs_secondary = test in {
            "Two-sample t-test",
            "Paired t-test",
            "One-way ANOVA",
            "Chi-square independence",
        }
        self.secondary.setEnabled(needs_secondary)
        self.method.setEnabled(test == "Correlation matrix")
        self.primary.setEnabled(test != "Descriptive statistics")

    def _selected(self) -> list[str]:
        return [item.text() for item in self.column_list.selectedItems()]

    def _emit(self, title: str, frame: pd.DataFrame | None, text: str) -> None:
        self.last_title = title
        self.model.set_frame(frame)
        self.interpretation.setHtml(text)
        self.resultReady.emit(title, frame)
        self.window().statusBar().showMessage(title, 6000)

    def run(self) -> None:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        df = self.manager.df
        test = self.test_combo.currentText()
        selection = self._selected() or self.manager.numeric_columns
        primary = self.primary.currentText()
        secondary = self.secondary.currentText()
        try:
            if test == "Descriptive statistics":
                frame = st.describe(df, selection)
                self._emit(
                    "Descriptive statistics",
                    frame,
                    f"<b>{len(frame)}</b> numeric variables summarised. "
                    "Compare mean vs median to judge skew, and use CV % to compare dispersion "
                    "across variables on different scales.",
                )
            elif test == "Correlation matrix":
                frame = st.correlation(df, selection, self.method.currentText())
                strongest = (
                    frame.where(~frame.isna())
                    .abs()
                    .where(lambda x: x < 0.999)
                    .stack()
                    .sort_values(ascending=False)
                )
                top = ""
                if not strongest.empty:
                    (a, b), value = strongest.index[0], strongest.iloc[0]
                    top = f" Strongest relationship: <b>{a}</b> and <b>{b}</b> (|r| = {value:.3f})."
                out = frame.reset_index(names="Variable")
                self._emit(
                    f"{self.method.currentText().title()} correlation matrix",
                    out,
                    f"Values range from -1 to 1.{top}",
                )
            elif test == "Frequency table":
                frame = st.frequency(df, primary)
                self._emit(
                    f"Frequency table for {primary}",
                    frame,
                    f"<b>{df[primary].nunique(dropna=True)}</b> distinct values; "
                    "the table lists the most common categories with their share of all rows.",
                )
            else:
                result = {
                    "Normality (Shapiro-Wilk)": lambda: st.normality(df, primary),
                    "Two-sample t-test": lambda: st.t_test(df, primary, secondary, False),
                    "Paired t-test": lambda: st.t_test(df, primary, secondary, True),
                    "One-way ANOVA": lambda: st.anova(df, primary, secondary),
                    "Chi-square independence": lambda: st.chi_square(df, primary, secondary),
                    "Linear regression (OLS)": lambda: st.linear_regression(
                        df, primary, [c for c in selection if c != primary]
                    ),
                }[test]()
                if "error" in result:
                    QMessageBox.warning(self, "Cannot run analysis", str(result["error"]))
                    return
                frame = result.pop("coefficients", None)
                rows = pd.DataFrame(
                    {"Metric": list(result.keys()), "Value": [str(v) for v in result.values()]}
                )
                self._emit(
                    str(result.get("test", test)),
                    frame if frame is not None else rows,
                    "<br>".join(f"<b>{k}</b>: {v}" for k, v in result.items()),
                )
        except Exception as exc:
            QMessageBox.warning(self, "Analysis failed", str(exc))

    def refresh(self) -> None:
        columns = self.manager.columns
        numeric = self.manager.numeric_columns
        selected = set(self._selected())
        self.column_list.clear()
        self.column_list.addItems(numeric or columns)
        for index in range(self.column_list.count()):
            item = self.column_list.item(index)
            if item.text() in selected:
                item.setSelected(True)
        for combo, values in ((self.primary, columns), (self.secondary, columns)):
            current = combo.currentText()
            combo.clear()
            combo.addItems(values)
            if current in values:
                combo.setCurrentText(current)
