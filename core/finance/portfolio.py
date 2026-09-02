"""Portfolio-level risk and performance metrics for DataSense.

All functions are pure with respect to caller-owned inputs. Inputs are expected to
be aligned return series; missing/non-finite observations are handled explicitly.
The module reports diagnostics, not forecasts or investment advice.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def _clean_series(values: pd.Series) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 2:
        raise ValueError("At least two finite observations are required.")
    return series.astype(float)


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized sample volatility from periodic returns."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    return float(_clean_series(returns).std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Annualized Sharpe ratio using a periodic risk-free rate."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    series = _clean_series(returns)
    excess = series - float(risk_free_rate)
    volatility = excess.std(ddof=1)
    if volatility == 0.0:
        return 0.0 if excess.mean() == 0.0 else float(np.sign(excess.mean()) * np.inf)
    return float(excess.mean() / volatility * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: pd.Series,
    target_return: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Annualized Sortino ratio using downside deviation below target_return."""
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    series = _clean_series(returns)
    excess = series - float(target_return)
    downside = np.minimum(excess.to_numpy(), 0.0)
    denominator = float(np.sqrt(np.mean(np.square(downside))))
    if denominator == 0.0:
        return 0.0 if excess.mean() == 0.0 else float(np.sign(excess.mean()) * np.inf)
    return float(excess.mean() / denominator * np.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown from periodic returns as a positive loss."""
    series = _clean_series(returns)
    wealth = (1.0 + series).cumprod()
    drawdown = wealth / wealth.cummax() - 1.0
    return float(max(0.0, -drawdown.min()))


def portfolio_returns(
    returns: Mapping[str, pd.Series] | pd.DataFrame,
    weights: Mapping[str, float],
) -> pd.Series:
    """Align named asset returns and compute a weighted portfolio return series.

    The weights must be finite and sum to approximately one. Missing observations
    are dropped only after all series are aligned so the portfolio timestamp set
    remains explicit and deterministic.
    """
    frame = returns.copy() if isinstance(returns, pd.DataFrame) else pd.concat(returns, axis=1)
    frame.columns = [str(column) for column in frame.columns]
    requested = [str(name) for name in weights]
    missing = [name for name in requested if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing return series: {', '.join(missing)}")
    if not weights:
        raise ValueError("At least one portfolio weight is required.")
    weight_values = np.asarray([float(weights[name]) for name in requested], dtype=float)
    if not np.isfinite(weight_values).all():
        raise ValueError("Portfolio weights must be finite.")
    if not np.isclose(weight_values.sum(), 1.0, atol=1e-9):
        raise ValueError("Portfolio weights must sum to 1.0.")
    aligned = frame[requested].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(aligned) < 2:
        raise ValueError("At least two aligned observations are required.")
    output = aligned.mul(weight_values, axis=1).sum(axis=1)
    output.name = "portfolio"
    return output


def risk_summary(
    returns: pd.Series,
    confidence: float = 0.95,
    periods_per_year: int = 252,
) -> dict[str, float | int | str]:
    """Return a compact, serializable risk summary for reports and dashboards."""
    from .risk import expected_shortfall, historical_var, parametric_var

    series = _clean_series(returns)
    return {
        "observations": int(len(series)),
        "mean_return": float(series.mean()),
        "annualized_volatility": annualized_volatility(series, periods_per_year),
        "sharpe_ratio": sharpe_ratio(series, 0.0, periods_per_year),
        "sortino_ratio": sortino_ratio(series, 0.0, periods_per_year),
        "max_drawdown": max_drawdown(series),
        "historical_var": historical_var(series, confidence),
        "parametric_var": parametric_var(series, confidence),
        "expected_shortfall": expected_shortfall(series, confidence),
        "confidence": float(confidence),
        "periods_per_year": int(periods_per_year),
    }
