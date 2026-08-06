"""Visualisation workspace with ten interactive chart types."""
from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.data_manager import DataManager
from .widgets.plot_canvas import PlotCanvas

CHARTS = [
    "Line chart",
    "Bar chart",
    "Horizontal bar chart",
    "Scatter plot",
    "Histogram",
    "Box plot",
    "Violin plot",
    "Pie chart",
    "Area chart",
    "Correlation heatmap",
]


class VisualizationTab(QWidget):
    def __init__(self, manager: DataManager, dark: bool = True) -> None:
        super().__init__()
        self.manager = manager
        self.canvas = PlotCanvas(dark)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        config = QGroupBox("Chart configuration")
        grid = QGridLayout(config)
        grid.addWidget(QLabel("Chart type"), 0, 0)
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(CHARTS)
        grid.addWidget(self.chart_combo, 0, 1)
        grid.addWidget(QLabel("X / category"), 1, 0)
        self.x_combo = QComboBox()
        grid.addWidget(self.x_combo, 1, 1)
        grid.addWidget(QLabel("Y / value"), 2, 0)
        self.y_combo = QComboBox()
        grid.addWidget(self.y_combo, 2, 1)
        grid.addWidget(QLabel("Group by (optional)"), 3, 0)
        self.group_combo = QComboBox()
        grid.addWidget(self.group_combo, 3, 1)
        grid.addWidget(QLabel("Bins / top-N"), 4, 0)
        self.bins = QSpinBox()
        self.bins.setRange(3, 200)
        self.bins.setValue(20)
        grid.addWidget(self.bins, 4, 1)
        grid.addWidget(QLabel("Title"), 5, 0)
        self.title_edit = QLineEdit()
        grid.addWidget(self.title_edit, 5, 1)
        self.legend_check = QCheckBox("Show legend")
        self.legend_check.setChecked(True)
        grid.addWidget(self.legend_check, 6, 0, 1, 2)
        layout.addWidget(config)

        draw = QPushButton("Render chart")
        draw.setProperty("accent", True)
        draw.clicked.connect(self.render_chart)
        layout.addWidget(draw)
        export = QPushButton("Export chart as image")
        export.clicked.connect(self.export_chart)
        layout.addWidget(export)
        layout.addStretch(1)
        panel.setMaximumWidth(360)
        splitter.addWidget(panel)

        canvas_box = QGroupBox("Chart")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.addWidget(self.canvas)
        splitter.addWidget(canvas_box)
        splitter.setSizes([340, 900])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------- rendering
    def render_chart(self) -> None:
        if not self.manager.loaded:
            QMessageBox.information(self, "No dataset", "Import a dataset first.")
            return
        df = self.manager.df
        chart = self.chart_combo.currentText()
        x, y = self.x_combo.currentText(), self.y_combo.currentText()
        group = self.group_combo.currentText()
        colors = self.canvas.color_cycle()
        ax = self.canvas.axes()
        try:
            if chart == "Correlation heatmap":
                numeric = df[self.manager.numeric_columns()].apply(
                    pd.to_numeric, errors="coerce"
                )
                matrix = numeric.corr()
                image = ax.imshow(matrix, cmap="viridis", vmin=-1, vmax=1)
                ax.set_xticks(range(len(matrix.columns)))
                ax.set_xticklabels(matrix.columns, rotation=45, ha="right")
                ax.set_yticks(range(len(matrix.columns)))
                ax.set_yticklabels(matrix.columns)
                ax.grid(False)
                self.canvas.figure.colorbar(image, ax=ax, shrink=0.85)
            elif chart == "Histogram":
                series = pd.to_numeric(df[y or x], errors="coerce").dropna()
                ax.hist(series, bins=self.bins.value(), color=colors[0], edgecolor="none")
                ax.set_xlabel(y or x)
                ax.set_ylabel("Frequency")
            elif chart in {"Box plot", "Violin plot"}:
                if group and group != "(none)":
                    groups = [
                        (str(key), pd.to_numeric(sub[y], errors="coerce").dropna())
                        for key, sub in df.groupby(group)
                    ][: self.bins.value()]
                else:
                    groups = [(y, pd.to_numeric(df[y], errors="coerce").dropna())]
                labels = [g[0] for g in groups]
                values = [g[1] for g in groups if not g[1].empty]
                if chart == "Box plot":
                    parts = ax.boxplot(values, patch_artist=True, labels=labels)
                    for patch, color in zip(parts["boxes"], colors * 10):
                        patch.set_facecolor(color)
                        patch.set_alpha(0.75)
                else:
                    parts = ax.violinplot(values, showmeans=True)
                    for body, color in zip(parts["bodies"], colors * 10):
                        body.set_facecolor(color)
                        body.set_alpha(0.7)
                    ax.set_xticks(range(1, len(labels) + 1))
                    ax.set_xticklabels(labels, rotation=30, ha="right")
                ax.set_ylabel(y)
            elif chart == "Pie chart":
                counts = df[x].value_counts().head(self.bins.value())
                ax.pie(
                    counts.to_numpy(),
                    labels=[str(i) for i in counts.index],
                    autopct="%1.1f%%",
                    colors=colors * 10,
                    textprops={"color": self.canvas._colors["text"], "fontsize": 9},
                )
                ax.grid(False)
                ax.set_aspect("equal")
            elif chart == "Scatter plot":
                data = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
                if group and group != "(none)":
                    joined = df.loc[data.index, group]
                    for color, (key, idx) in zip(
                        colors * 10, joined.groupby(joined).groups.items()
                    ):
                        ax.scatter(
                            data.loc[idx, x], data.loc[idx, y], s=22, alpha=0.8,
                            color=color, label=str(key)
                        )
                else:
                    ax.scatter(data[x], data[y], s=22, alpha=0.8, color=colors[0], label=y)
                    if len(data) > 2:
                        slope, intercept = np.polyfit(data[x], data[y], 1)
                        xs = np.linspace(data[x].min(), data[x].max(), 50)
                        ax.plot(xs, slope * xs + intercept, color=colors[1], linewidth=2,
                                label="trend")
                ax.set_xlabel(x)
                ax.set_ylabel(y)
            elif chart in {"Bar chart", "Horizontal bar chart"}:
                if pd.api.types.is_numeric_dtype(df[y]):
                    agg = df.groupby(x)[y].mean().sort_values(ascending=False)
                else:
                    agg = df[x].value_counts()
                agg = agg.head(self.bins.value())
                labels = [str(i) for i in agg.index]
                if chart == "Bar chart":
                    ax.bar(labels, agg.to_numpy(), color=colors[0])
                    ax.set_xticklabels(labels, rotation=35, ha="right")
                    ax.set_ylabel(y)
                else:
                    ax.barh(labels[::-1], agg.to_numpy()[::-1], color=colors[1])
                    ax.set_xlabel(y)
            else:  # Line and Area charts
                data = df.copy()
                ordered = data.sort_values(x) if x in data.columns else data
                ys = pd.to_numeric(ordered[y], errors="coerce")
                xs = ordered[x]
                if chart == "Area chart":
                    ax.fill_between(range(len(ys)), ys.fillna(0), color=colors[0], alpha=0.45)
                ax.plot(range(len(ys)), ys, color=colors[0], linewidth=2, label=y)
                step = max(len(xs) // 12, 1)
                ax.set_xticks(range(0, len(xs), step))
                ax.set_xticklabels([str(v) for v in xs[::step]], rotation=35, ha="right")
                ax.set_xlabel(x)
                ax.set_ylabel(y)

            title = self.title_edit.text().strip() or f"{chart}"
            ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
            if self.legend_check.isChecked() and ax.get_legend_handles_labels()[0]:
                legend = ax.legend(frameon=False)
                for text in legend.get_texts():
                    text.set_color(self.canvas._colors["muted"])
            self.canvas.refresh()
            self.window().statusBar().showMessage(f"Rendered {chart}", 5000)
        except Exception as exc:
            QMessageBox.warning(self, "Chart failed", str(exc))

    def export_chart(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export chart", "chart.png", "PNG image (*.png);;SVG vector (*.svg);;PDF (*.pdf)"
        )
        if not path:
            return
        self.canvas.figure.savefig(path, dpi=200, bbox_inches="tight",
                                   facecolor=self.canvas.figure.get_facecolor())
        self.window().statusBar().showMessage(f"Chart exported to {path}", 6000)

    def apply_theme(self, dark: bool) -> None:
        self.canvas.apply_theme(dark)

    def refresh(self) -> None:
        columns = self.manager.columns()
        numeric = self.manager.numeric_columns()
        for combo, values in (
            (self.x_combo, columns),
            (self.y_combo, numeric or columns),
            (self.group_combo, ["(none)"] + self.manager.categorical_columns()),
        ):
            current = combo.currentText()
            combo.clear()
            combo.addItems(values)
            if current in values:
                combo.setCurrentText(current)
