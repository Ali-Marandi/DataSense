"""SQL console workspace: query DataFrames with real SQL."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QRegularExpression, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.sql import SQLEngine

KEYWORDS = [
    "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "JOIN",
    "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AS", "AND", "OR", "NOT", "IN",
    "DISTINCT", "COUNT", "SUM", "AVG", "MIN", "MAX", "CASE", "WHEN", "THEN",
    "ELSE", "END", "WITH", "UNION", "BETWEEN", "LIKE", "IS", "NULL", "DESC", "ASC",
]


class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        keyword = QTextCharFormat()
        keyword.setForeground(QColor("#5ac8b0"))
        keyword.setFontWeight(QFont.Weight.Bold)
        string = QTextCharFormat()
        string.setForeground(QColor("#e0a84a"))
        number = QTextCharFormat()
        number.setForeground(QColor("#8ab4ff"))
        comment = QTextCharFormat()
        comment.setForeground(QColor("#7c8ba1"))

        self.rules = [
            (QRegularExpression(r"\b" + kw.replace(" ", r"\s+") + r"\b",
                                QRegularExpression.PatternOption.CaseInsensitiveOption), keyword)
            for kw in KEYWORDS
        ]
        self.rules += [
            (QRegularExpression(r"'[^']*'"), string),
            (QRegularExpression(r"\b\d+(\.\d+)?\b"), number),
            (QRegularExpression(r"--[^\n]*"), comment),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class SQLTab(QWidget):
    dataChanged = pyqtSignal()
    resultReady = pyqtSignal(str, object)

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager
        self.engine: SQLEngine | None = None
        self.last_result: pd.DataFrame | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        bar = QHBoxLayout()
        self.table_picker = QComboBox()
        self.table_picker.currentTextChanged.connect(self._insert_template)
        self.run_btn = QPushButton("Run query  (Ctrl+Enter)")
        self.run_btn.clicked.connect(self.run_query)
        self.apply_btn = QPushButton("Replace dataset with result")
        self.apply_btn.clicked.connect(self.apply_result)
        self.apply_btn.setEnabled(False)
        bar.addWidget(QLabel("Tables:"))
        bar.addWidget(self.table_picker, 1)
        bar.addWidget(self.run_btn)
        bar.addWidget(self.apply_btn)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("SELECT * FROM data LIMIT 100")
        self.editor.setFont(QFont("Consolas", 11))
        self.highlighter = SQLHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        splitter.addWidget(self.table)
        splitter.setSizes([220, 480])
        root.addWidget(splitter, 1)

        self.status = QLabel("Load a dataset, then query it as the table 'data'.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    # ------------------------------------------------------------------ logic
    def refresh(self) -> None:
        if self.engine is not None:
            self.engine.close()
            self.engine = None
        self.table_picker.clear()
        if not self.manager.loaded:
            self.status.setText("No dataset loaded.")
            return
        self.engine = SQLEngine()
        self.engine.register("data", self.manager.df)
        for name, frame in getattr(self.manager, "versions", {}).items():
            self.engine.register(f"v_{name}", frame)
        self.table_picker.addItems(self.engine.list_tables())
        if not self.editor.toPlainText().strip():
            self.editor.setPlainText("SELECT * FROM data LIMIT 100")
        self.status.setText(
            f"{len(self.engine.list_tables())} table(s) registered — main table is 'data'."
        )

    def _insert_template(self, table: str) -> None:
        if table and not self.editor.toPlainText().strip():
            self.editor.setPlainText(f"SELECT * FROM {table} LIMIT 100")

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.run_query()
            return
        super().keyPressEvent(event)

    def run_query(self) -> None:
        if self.engine is None:
            self.refresh()
        if self.engine is None:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        result = self.engine.execute(self.editor.toPlainText())
        self.status.setText(result.message)
        if not result.ok:
            self.apply_btn.setEnabled(False)
            return
        self.last_result = result.frame
        self.apply_btn.setEnabled(result.frame is not None and not result.frame.empty)
        self._show(result.frame)
        if result.frame is not None and not result.frame.empty:
            self.resultReady.emit("SQL query result", result.frame.head(50))

    def _show(self, frame: pd.DataFrame | None) -> None:
        if frame is None or frame.empty:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        preview = frame.head(1000)
        self.table.setColumnCount(preview.shape[1])
        self.table.setRowCount(len(preview))
        self.table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        for r in range(len(preview)):
            for c in range(preview.shape[1]):
                self.table.setItem(r, c, QTableWidgetItem(str(preview.iat[r, c])))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.resizeColumnsToContents()

    def apply_result(self) -> None:
        if self.last_result is None or self.last_result.empty:
            return
        self.manager.set_frame(self.last_result, "SQL query applied")
        self.dataChanged.emit()
        self.status.setText("Active dataset replaced with the query result.")
