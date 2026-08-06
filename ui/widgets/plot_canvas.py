"""Matplotlib canvas themed to match the application palette."""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..theme import palette


class PlotCanvas(QWidget):
    def __init__(self, dark: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.figure = Figure(figsize=(6, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.apply_theme(dark)

    def apply_theme(self, dark: bool) -> None:
        self._colors = palette(dark)
        self.figure.set_facecolor(self._colors["surface"])
        self.canvas.draw_idle()

    def axes(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        c = self._colors
        ax.set_facecolor(c["surface"])
        for spine in ax.spines.values():
            spine.set_color(c["border"])
        ax.tick_params(colors=c["muted"], labelsize=9)
        ax.xaxis.label.set_color(c["text"])
        ax.yaxis.label.set_color(c["text"])
        ax.title.set_color(c["text"])
        ax.grid(True, color=c["grid"], linewidth=0.7, alpha=0.8)
        ax.set_axisbelow(True)
        return ax

    def refresh(self) -> None:
        self.figure.set_facecolor(self._colors["surface"])
        self.canvas.draw_idle()

    def color_cycle(self) -> list[str]:
        c = self._colors
        return [c["primary"], c["accent"], "#f59e0b", "#a78bfa", "#f472b6", "#4ade80", "#fb923c"]
