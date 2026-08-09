"""Overview workspace: health score, KPIs and automatic insights."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.insights import generate_insights, health_score, summary_metrics

SEVERITY_COLOR = {"critical": "#e4586a", "warning": "#e0a84a", "info": "#3fbfa8"}


class KPICard(QFrame):
    def __init__(self, title: str, value: str = "-") -> None:
        super().__init__()
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.caption = QLabel(title.upper())
        self.caption.setStyleSheet("font-size:10px;letter-spacing:1px;opacity:.7;")
        self.value = QLabel(value)
        self.value.setStyleSheet("font-size:22px;font-weight:600;")
        layout.addWidget(self.caption)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class OverviewTab(QWidget):
    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        self.title = QLabel("No dataset loaded")
        self.title.setStyleSheet("font-size:19px;font-weight:600;")
        self.refresh_btn = QPushButton("Re-scan dataset")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.title, 1)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        score_box = QVBoxLayout()
        self.score_label = QLabel("Health score: -")
        self.score_label.setStyleSheet("font-size:14px;font-weight:600;")
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setTextVisible(False)
        self.score_bar.setFixedHeight(14)
        score_box.addWidget(self.score_label)
        score_box.addWidget(self.score_bar)
        root.addLayout(score_box)

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(12)
        self.cards: dict[str, KPICard] = {}
        for i, name in enumerate(
            ["Rows", "Columns", "Missing cells", "Duplicate rows", "Numeric columns", "Health score"]
        ):
            card = KPICard(name)
            self.cards[name] = card
            self.kpi_grid.addWidget(card, i // 3, i % 3)
        root.addLayout(self.kpi_grid)

        root.addWidget(QLabel("Automatic insights"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Severity", "Area", "Insight", "Detail"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

    def refresh(self) -> None:
        df: pd.DataFrame | None = self.manager.df
        if df is None or df.empty:
            self.title.setText("No dataset loaded")
            self.score_label.setText("Health score: -")
            self.score_bar.setValue(0)
            for card in self.cards.values():
                card.set_value("-")
            self.table.setRowCount(0)
            return

        source = self.manager.source or "in-memory dataset"
        self.title.setText(f"{source}")
        score = health_score(df)
        self.score_label.setText(f"Health score: {score:.1f} / 100")
        self.score_bar.setValue(int(score))
        colour = "#e4586a" if score < 50 else ("#e0a84a" if score < 80 else "#3fbfa8")
        self.score_bar.setStyleSheet(
            f"QProgressBar{{border-radius:7px;background:rgba(128,128,128,.25);}}"
            f"QProgressBar::chunk{{border-radius:7px;background:{colour};}}"
        )

        for name, value in summary_metrics(df).items():
            if name in self.cards:
                self.cards[name].set_value(str(value))

        insights = generate_insights(df)
        self.table.setRowCount(len(insights))
        for row, insight in enumerate(insights):
            items = [insight.severity, insight.category, insight.title, insight.detail]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setForeground(Qt.GlobalColor.white)
                    item.setToolTip(insight.severity)
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
