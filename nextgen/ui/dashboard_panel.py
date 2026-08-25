from __future__ import annotations

from collections.abc import Sequence

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.data.model import DatasetProfile
from core.governance.contracts import QualityReport


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str = "#5a8cff") -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setProperty("accent", accent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        self.title = QLabel(title)
        self.title.setObjectName("metricTitle")
        self.value = QLabel("—")
        self.value.setObjectName("metricValue")
        self.detail = QLabel("No dataset loaded")
        self.detail.setObjectName("metricDetail")
        self.detail.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_metric(self, value: str, detail: str) -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class QualityPulse(QWidget):
    """Tiny painted quality signal; it visualizes aggregate counts, never raw data."""

    def __init__(self) -> None:
        super().__init__()
        self._values: tuple[int, ...] = ()
        self.setMinimumHeight(86)
        self.setObjectName("qualityPulse")

    def set_values(self, values: Sequence[int]) -> None:
        self._values = tuple(max(0, int(value)) for value in values)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111b2d"))
        if not self._values:
            painter.setPen(QColor("#8ea0bd"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Load data to view health signal")
            return
        maximum = max(max(self._values), 1)
        margin = 14
        usable_width = max(1, self.width() - 2 * margin)
        usable_height = max(1, self.height() - 2 * margin)
        points = QPolygonF()
        for index, value in enumerate(self._values):
            x = margin + usable_width * index / max(1, len(self._values) - 1)
            y = margin + usable_height * (1 - value / maximum)
            points.append(QPointF(x, y))
        painter.setPen(QPen(QColor("#47d7ac"), 2.4))
        painter.drawPolyline(points)
        painter.setBrush(QColor("#8cf1d1"))
        painter.setPen(Qt.PenStyle.NoPen)
        for point in points:
            painter.drawEllipse(point, 3.3, 3.3)


class DashboardPanel(QWidget):
    """Read-only dashboard projection of ApplicationState.

    It accepts domain objects from core and never performs dataframe analysis itself.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dashboardPanel")
        self._build_ui()
        self.update_dashboard(None, None, "No dataset loaded")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("dashboardHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_text = QVBoxLayout()
        heading = QLabel("Data operations cockpit")
        heading.setObjectName("dashboardHeading")
        subheading = QLabel("A local, privacy-first overview of your dataset, data health and verified delivery readiness.")
        subheading.setObjectName("muted")
        subheading.setWordWrap(True)
        hero_text.addWidget(heading)
        hero_text.addWidget(subheading)
        self.source_label = QLabel()
        self.source_label.setObjectName("sourceLabel")
        hero_text.addWidget(self.source_label)
        hero_layout.addLayout(hero_text, 1)
        self.trust_badge = QLabel()
        self.trust_badge.setObjectName("trustBadge")
        self.trust_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trust_badge.setMinimumWidth(160)
        hero_layout.addWidget(self.trust_badge)
        layout.addWidget(hero)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self.metric_cards = {
            "rows": MetricCard("ROWS", "#62a2ff"),
            "columns": MetricCard("COLUMNS", "#c596ff"),
            "missing": MetricCard("MISSING CELLS", "#ffbd59"),
            "duplicates": MetricCard("DUPLICATE ROWS", "#ff7885"),
        }
        for index, card in enumerate(self.metric_cards.values()):
            metrics.addWidget(card, 0, index)
        layout.addLayout(metrics)

        detail_grid = QGridLayout()
        detail_grid.setHorizontalSpacing(14)
        pulse_card = QFrame()
        pulse_card.setObjectName("card")
        pulse_layout = QVBoxLayout(pulse_card)
        pulse_layout.setContentsMargins(18, 16, 18, 16)
        pulse_title = QLabel("DATA HEALTH SIGNAL")
        pulse_title.setObjectName("sectionTitle")
        pulse_layout.addWidget(pulse_title)
        self.pulse = QualityPulse()
        pulse_layout.addWidget(self.pulse)
        self.health_label = QLabel()
        self.health_label.setObjectName("muted")
        pulse_layout.addWidget(self.health_label)
        detail_grid.addWidget(pulse_card, 0, 0)

        quality_card = QFrame()
        quality_card.setObjectName("card")
        quality_layout = QVBoxLayout(quality_card)
        quality_layout.setContentsMargins(18, 16, 18, 16)
        quality_layout.addWidget(self._section_label("VERIFICATION GATE"))
        self.quality_progress = QProgressBar()
        self.quality_progress.setRange(0, 100)
        self.quality_progress.setTextVisible(True)
        quality_layout.addWidget(self.quality_progress)
        self.quality_message = QLabel()
        self.quality_message.setWordWrap(True)
        quality_layout.addWidget(self.quality_message)
        quality_layout.addStretch()
        detail_grid.addWidget(quality_card, 0, 1)
        detail_grid.setColumnStretch(0, 3)
        detail_grid.setColumnStretch(1, 2)
        layout.addLayout(detail_grid)

        table_card = QFrame()
        table_card.setObjectName("card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 16, 18, 16)
        table_layout.addWidget(self._section_label("COLUMN PROFILE"))
        self.columns_table = QTableWidget(0, 4)
        self.columns_table.setObjectName("columnsTable")
        self.columns_table.setHorizontalHeaderLabels(["Column", "Type", "Missing", "Unique"])
        self.columns_table.verticalHeader().setVisible(False)
        self.columns_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.columns_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.columns_table.setAlternatingRowColors(True)
        self.columns_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.columns_table)
        layout.addWidget(table_card, 1)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def update_dashboard(
        self,
        profile: DatasetProfile | None,
        quality: QualityReport | None,
        source_label: str,
    ) -> None:
        self.source_label.setText(source_label)
        if profile is None:
            for card in self.metric_cards.values():
                card.set_metric("—", "No dataset loaded")
            self.pulse.set_values(())
            self.health_label.setText("Metrics remain local and will appear after import.")
            self.columns_table.setRowCount(0)
            self._render_quality(quality)
            return

        self.metric_cards["rows"].set_metric(f"{profile.rows:,}", "Local records")
        self.metric_cards["columns"].set_metric(str(profile.columns), "Detected fields")
        self.metric_cards["missing"].set_metric(f"{profile.missing_cells:,}", "Values requiring review")
        self.metric_cards["duplicates"].set_metric(f"{profile.duplicate_rows:,}", "Exact repeated records")
        self.pulse.set_values((profile.rows, profile.columns, profile.missing_cells, profile.duplicate_rows))
        self.health_label.setText(
            f"{profile.rows:,} records profiled locally · {profile.memory_mb:.2f} MB estimated in-memory footprint"
        )
        self._populate_column_table(profile)
        self._render_quality(quality)

    def _populate_column_table(self, profile: DatasetProfile) -> None:
        self.columns_table.setRowCount(len(profile.column_summaries))
        for row, summary in enumerate(profile.column_summaries):
            values = (summary.name, summary.dtype, str(summary.missing), str(summary.unique))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.columns_table.setItem(row, column, item)
        self.columns_table.resizeColumnsToContents()

    def _render_quality(self, quality: QualityReport | None) -> None:
        if quality is None:
            self.trust_badge.setText("CHECKS\nNOT RUN")
            self.trust_badge.setProperty("state", "pending")
            self.quality_progress.setValue(0)
            self.quality_progress.setFormat("Run quality checks")
            self.quality_message.setText("Verified delivery stays locked until the active contract is evaluated.")
        elif quality.approved:
            self.trust_badge.setText("VERIFIED\nREADY")
            self.trust_badge.setProperty("state", "approved")
            self.quality_progress.setValue(100)
            self.quality_progress.setFormat("All blocking checks passed")
            self.quality_message.setText(f"{len(quality.results)} rule(s) evaluated; verified export is available.")
        else:
            self.trust_badge.setText("ACTION\nREQUIRED")
            self.trust_badge.setProperty("state", "blocked")
            passed = len(quality.results) - len(quality.failures)
            percent = int(100 * passed / max(1, len(quality.results)))
            self.quality_progress.setValue(percent)
            self.quality_progress.setFormat(f"{len(quality.blocking_failures)} blocking issue(s)")
            self.quality_message.setText("Resolve critical or high-severity findings before creating a verified artifact.")
        self.trust_badge.style().unpolish(self.trust_badge)
        self.trust_badge.style().polish(self.trust_badge)
