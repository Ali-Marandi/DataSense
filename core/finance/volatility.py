"""Volatility and risk helpers for DataSense finance features.

This module provides a thin wrapper around the `arch` library to fit a
GARCH(1,1) model and compute VaR/CVaR using a few simple methods.
"""
from __future__ import annotations

from typing import Tuple
import numpy as np
import pandas as pd

try:
    from arch import arch_model
except Exception as exc:  # pragma: no cover - imported in tests when available
    arch_model = None  # type: ignore


def fit_garch(returns: pd.Series, p: int = 1, q: int = 1, mean: str = "zero"):
    """
    Fit a GARCH(p,q) model to a returns series.

    Returns the fitted arch model result object.
    """
    if arch_model is None:
        raise RuntimeError("arch package is not installed; install 'arch' to use GARCH features")
    # ensure we work with returns (not prices)
    r = returns.dropna()
    if r.empty:
        raise ValueError("Empty returns series")
    # arch expects a 1d array-like of returns (typically percentages or decimal returns)
    am = arch_model(r, vol="Garch", p=p, q=q, mean=mean, dist="normal")
    res = am.fit(disp="off")
    return res


def forecast_volatility(fitted_model, horizon: int = 1) -> pd.Series:
    """
    Forecast conditional volatility for the given horizon (in periods).

    Returns a pandas Series indexed 1..horizon of sigma forecasts.
    """
    if fitted_model is None:
        raise ValueError("fitted_model is required")
    fc = fitted_model.forecast(horizon=horizon)
    # For many versions, the variance forecasts are in .variance and columns are integer steps
    var_fc = fc.variance.iloc[-1]
    sigma = np.sqrt(var_fc)
    # convert to Series with 1-based horizon index
    return pd.Series(sigma.values, index=list(range(1, len(sigma) + 1)))


def var_historical(returns: pd.Series, alpha: float = 0.01) -> float:
    """Historical VaR at level alpha (positive number representing loss).

    Example: alpha=0.01 gives 1% worst-case loss (positive value).
    """
    r = returns.dropna()
    if r.empty:
        raise ValueError("Empty returns series")
    q = np.quantile(r, alpha)
    return float(-q)


def var_parametric(returns: pd.Series, alpha: float = 0.01) -> float:
    """Parametric normal VaR using sample mean and std (one-period).

    Returns positive loss magnitude.
    """
    r = returns.dropna()
    mu = float(r.mean())
    sigma = float(r.std(ddof=1))
    z = np.abs(np.percentile(r, 100 * alpha))  # fallback
    # use normal quantile (inverse cdf)
    from scipy.stats import norm

    z = norm.ppf(alpha)
    var = -(mu + z * sigma)
    return float(var)


def var_garch(returns: pd.Series, fitted_model, alpha: float = 0.01, horizon: int = 1) -> float:
    """Compute VaR using a GARCH forecast for volatility.

    - fitted_model: result of fit_garch
    - horizon: forecast horizon in periods
    """
    if fitted_model is None:
        raise ValueError("fitted_model is required for var_garch")
    sigma_fc = forecast_volatility(fitted_model, horizon=horizon).iloc[horizon - 1]
    mu = float(returns.dropna().mean())
    from scipy.stats import norm

    z = norm.ppf(alpha)
    var = -(mu + z * sigma_fc)
    return float(var)
