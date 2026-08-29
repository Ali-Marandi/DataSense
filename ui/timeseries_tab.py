"""Time-series workspace: resampling, decomposition and forecasting."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.timeseries import FREQUENCIES, MODELS, build_series, decompose, forecast, forecast_frame
from core.finance.factors import compute_beta

AGGREGATIONS = ["sum", "mean", "median", "min", "max", "count"]


class TimeSeriesTab(QWidget):
    resultReady = pyqtSignal(str, object)

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        controls = QGroupBox("Series definition")
        form = QFormLayout(controls)
        controls.setMaximumWidth(340)
        self.date_box = QComboBox()
        self.value_box = QComboBox()
        self.freq_box = QComboBox()
        self.freq_box.addItems(list(FREQUENCIES.keys()))
        self.freq_box.setCurrentText("Daily")
        self.agg_box = QComboBox()
        self.agg_box.addItems(AGGREGATIONS)
        self.model_box = QComboBox()
        self.model_box.addItems(MODELS)
        self.periods = QSpinBox()
        self.periods.setRange(1, 365)
        self.periods.setValue(14)

        form.addRow("Date column", self.date_box)
        form.addRow("Value column", self.value_box)
        form.addRow("Frequency", self.freq_box)
        form.addRow("Aggregation", self.agg_box)
        form.addRow("Model", self.model_box)
        form.addRow("Horizon", self.periods)

        # Market selector for finance calculations
        self.market_box = QComboBox()
        form.addRow("Market column", self.market_box)

        self.plot_btn = QPushButton("Plot series")
        self.decompose_btn = QPushButton("Decompose (trend / seasonality)")
        self.forecast_btn = QPushButton("Forecast")
        self.beta_btn = QPushButton("Compute Beta vs Market")
        for btn, slot in (
            (self.plot_btn, self.plot_series),
            (self.decompose_btn, self.run_decompose),
            (self.forecast_btn, self.run_forecast),
            (self.beta_btn, self.compute_beta_ui),
        ):
            btn.clicked.connect(slot)
            form.addRow(btn)

        self.metrics = QLabel("")
        self.metrics.setWordWrap(True)
        form.addRow(self.metrics)

        root.addWidget(controls)

        right = QVBoxLayout()
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        right.addWidget(self.canvas, 1)
        self.status = QLabel("Pick a date column and a numeric value column.")
        self.status.setWordWrap(True)
        right.addWidget(self.status)
        root.addLayout(right, 1)

    # ------------------------------------------------------------------ utils
    def refresh(self) -> None:
        if not self.manager.loaded:
            self.date_box.clear()
            self.value_box.clear()
            self.market_box.clear()
            return
        df = self.manager.df
        candidates = [
            c for c in df.columns
            if pd.api.types.is_datetime64_any_dtype(df[c])
            or "date" in str(c).lower() or "time" in str(c).lower()
        ] or list(df.columns)
        self._fill(self.date_box, candidates)
        self._fill(self.value_box, self.manager.numeric_columns)
        # fill market choices from numeric columns as well
        self._fill(self.market_box, self.manager.numeric_columns)

    @staticmethod
    def _fill(box: QComboBox, values: list[str]) -> None:
        current = box.currentText()
        box.blockSignals(True)
        box.clear()
        box.addItems([str(v) for v in values])
        if current in values:
            box.setCurrentText(current)
        box.blockSignals(False)

    def _series(self):
        if not self.manager.loaded:
            raise ValueError("No dataset loaded.")
        date_col = self.date_box.currentText()
        value_col = self.value_box.currentText()
        if not date_col or not value_col:
            raise ValueError("Select both a date column and a value column.")
        return build_series(
            self.manager.df, date_col, value_col,
            FREQUENCIES[self.freq_box.currentText()], self.agg_box.currentText(),
        )

    def _fail(self, exc: Exception) -> None:
        self.status.setText(str(exc))
        QMessageBox.warning(self, "Time series", str(exc))

    # ---------------------------------------------------------------- actions
    def plot_series(self) -> None:
        try:
            series = self._series()
        except Exception as exc:
            self._fail(exc)
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(series.index, series.values, color="#22c1a4", linewidth=1.6)
        ax.set_title(f"{self.value_box.currentText()} over time")
        ax.grid(alpha=0.25)
        self.canvas.draw_idle()
        self.status.setText(f"{len(series):,} periods from {series.index.min()} to {series.index.max()}.")

    def run_decompose(self) -> None:
        try:
            series = self._series()
            parts = decompose(series)
        except Exception as exc:
            self._fail(exc)
            return
        self.figure.clear()
        axes = self.figure.subplots(4, 1, sharex=True)
        for ax, (name, colour) in zip(
            axes,
            [("observed", "#22c1a4"), ("trend", "#4f9dff"),
             ("seasonal", "#e0a84a"), ("residual", "#e4586a")],
        ):
            ax.plot(parts.index, parts[name], color=colour, linewidth=1.2)
            ax.set_ylabel(name, fontsize=8)
            ax.grid(alpha=0.2)
        self.canvas.draw_idle()
        self.status.setText("Seasonal decomposition complete.")
        self.resultReady.emit("Seasonal decomposition", parts.tail(30).reset_index())

    def run_forecast(self) -> None:
        try:
            series = self._series()
            result = forecast(series, self.periods.value(), self.model_box.currentText())
        except Exception as exc:
            self._fail(exc)
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(result.history.index, result.history.values, color="#8ab4ff", label="history")
        ax.plot(result.forecast.index, result.forecast.values, color="#22c1a4",
                linewidth=2, label=f"forecast ({result.model})")
        if result.lower is not None and result.upper is not None:
            ax.fill_between(result.forecast.index, result.lower.values, result.upper.values,
                            color="#22c1a4", alpha=0.18, label="95% interval")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
        ax.set_title(f"Forecast — {self.value_box.currentText()}")
        self.canvas.draw_idle()
        self.metrics.setText(
            " · ".join(f"{k}: {v}" for k, v in result.metrics.items())
        )
        self.status.setText(f"Forecast of {self.periods.value()} period(s) generated.")
        self.resultReady.emit("Forecast", forecast_frame(result))

    def compute_beta_ui(self) -> None:
        try:
            asset_series = self._series()
            market_col = self.market_box.currentText()
            if not market_col:
                raise ValueError("Select a market column.")
            # Build market series using same date/aggregation settings
            market_series = build_series(
                self.manager.df, self.date_box.currentText(), market_col,
                FREQUENCIES[self.freq_box.currentText()], self.agg_box.currentText()
            )
            res = compute_beta(asset_series, market_series)
        except Exception as exc:
            self._fail(exc)
            return

        # plot scatter of returns and regression line
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        x = res["market_returns"].values
        y = res["asset_returns"].values
        ax.scatter(x, y, s=18, alpha=0.75, color="#4f9dff", label="observations")
        import numpy as np
        yhat = res["alpha"] + res["beta"] * x
        order = np.argsort(x)
        ax.plot(x[order], yhat[order], color="#e4586a", linewidth=1.6, label="fit")
        ax.set_title(f"Beta: {res['beta']:.3f}  ·  R²: {res['r2']:.3f}")
        ax.set_xlabel("market returns")
        ax.set_ylabel("asset returns")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
        self.canvas.draw_idle()

        self.status.setText(f"Beta: {res['beta']:.4f}  ·  R²: {res['r2']:.3f}  ·  n={res['n_obs']}")
        self.metrics.setText(f"alpha: {res['alpha']:.6f}")
        try:
            out_frame = res["asset_returns"].to_frame("asset_returns").join(res["market_returns"].to_frame("market_returns"))
            self.resultReady.emit("Beta regression", out_frame.reset_index())
        except Exception:
            pass

    def apply_theme(self, dark: bool) -> None:
        colour = "#141d2c" if dark else "#ffffff"
        text = "#e8eef7" if dark else "#16202f"
        self.figure.patch.set_facecolor(colour)
        for ax in self.figure.get_axes():
            ax.set_facecolor(colour)
            ax.tick_params(colors=text, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(text)
        self.canvas.draw_idle()
