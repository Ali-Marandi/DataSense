"""Financial analysis workspace for DataSense.

This tab exposes Beta, Volatility and simple network analyses based on the
core.finance helpers. It's intentionally lightweight and reuses existing
manager/dataframe plumbing."""
from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import pyqtSignal
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

from core.finance.factors import compute_beta
from core.finance.volatility import var_historical, fit_garch, var_parametric, var_garch
from core.timeseries import FREQUENCIES, build_series


class FinancialTab(QWidget):
    resultReady = pyqtSignal(str, object)

    def __init__(self, manager) -> None:
        super().__init__()
        self.manager = manager

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        controls = QGroupBox("Financial analysis")
        form = QFormLayout(controls)
        controls.setMaximumWidth(360)

        self.date_box = QComboBox()
        self.asset_box = QComboBox()
        self.market_box = QComboBox()
        self.freq_box = QComboBox()
        self.freq_box.addItems(list(FREQUENCIES.keys()))
        self.freq_box.setCurrentText("Daily")

        # Beta controls
        form.addRow("Date column", self.date_box)
        form.addRow("Asset column", self.asset_box)
        form.addRow("Market column", self.market_box)
        self.beta_btn = QPushButton("Compute Beta")
        self.beta_btn.clicked.connect(self.compute_beta_ui)
        form.addRow(self.beta_btn)

        # Volatility / VaR controls
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 365)
        self.window_spin.setValue(20)
        form.addRow("Return window (days)", self.window_spin)
        self.var_hist_btn = QPushButton("VaR (historical, 1%)")
        self.var_hist_btn.clicked.connect(self.compute_var_historical)
        form.addRow(self.var_hist_btn)
        self.var_param_btn = QPushButton("VaR (parametric, 1%)")
        self.var_param_btn.clicked.connect(self.compute_var_parametric)
        form.addRow(self.var_param_btn)
        self.garch_btn = QPushButton("Fit GARCH(1,1) & VaR")
        self.garch_btn.clicked.connect(self.compute_garch_and_var)
        form.addRow(self.garch_btn)

        self.metrics = QLabel("")
        self.metrics.setWordWrap(True)
        form.addRow(self.metrics)

        root.addWidget(controls)

        right = QVBoxLayout()
        self.figure = Figure(figsize=(7, 5), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        right.addWidget(self.canvas, 1)
        self.status = QLabel("Select asset and market columns and choose an analysis.")
        self.status.setWordWrap(True)
        right.addWidget(self.status)
        root.addLayout(right, 1)

    def refresh(self) -> None:
        if not self.manager.loaded:
            self.date_box.clear()
            self.asset_box.clear()
            self.market_box.clear()
            return
        df = self.manager.df
        candidates = [
            c for c in df.columns
            if pd.api.types.is_datetime64_any_dtype(df[c])
            or "date" in str(c).lower() or "time" in str(c).lower()
        ] or list(df.columns)
        self._fill(self.date_box, candidates)
        self._fill(self.asset_box, self.manager.numeric_columns)
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

    def _build_series(self, col: str):
        return build_series(self.manager.df, self.date_box.currentText(), col,
                            FREQUENCIES[self.freq_box.currentText()], "mean")

    def _fail(self, exc: Exception) -> None:
        self.status.setText(str(exc))
        QMessageBox.warning(self, "Financial analysis", str(exc))

    def compute_beta_ui(self) -> None:
        try:
            asset_series = self._build_series(self.asset_box.currentText())
            market_series = self._build_series(self.market_box.currentText())
            res = compute_beta(asset_series, market_series)
        except Exception as exc:
            self._fail(exc)
            return

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

    def compute_returns(self, col: str):
        s = self._build_series(col)
        # use simple returns for VaR calculations
        return s.pct_change().dropna()

    def compute_var_historical(self) -> None:
        try:
            r = self.compute_returns(self.asset_box.currentText())
            v = var_historical(r, alpha=0.01)
        except Exception as exc:
            self._fail(exc)
            return
        self.status.setText(f"Historical VaR(1%): {v:.4f}")
        self.metrics.setText("")

    def compute_var_parametric(self) -> None:
        try:
            r = self.compute_returns(self.asset_box.currentText())
            v = var_parametric(r, alpha=0.01)
        except Exception as exc:
            self._fail(exc)
            return
        self.status.setText(f"Parametric VaR(1%): {v:.4f}")
        self.metrics.setText("")

    def compute_garch_and_var(self) -> None:
        try:
            r = self.compute_returns(self.asset_box.currentText())
            # fit GARCH on returns (as decimals)
            fitted = fit_garch(r)
            v = var_garch(r, fitted, alpha=0.01, horizon=1)
        except Exception as exc:
            self._fail(exc)
            return
        self.status.setText(f"GARCH VaR(1%): {v:.4f}")
        self.metrics.setText("")
        try:
            self.resultReady.emit("GARCH VaR", pd.DataFrame({"var": [v]}))
        except Exception:
            pass
