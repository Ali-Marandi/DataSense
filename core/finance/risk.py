"""Risk analytics primitives for DataSense finance workflows.

The functions operate on return series and never mutate caller-owned data.
All VaR functions return a positive loss threshold: a 95% VaR of 0.02 means
an estimated one-period loss of 2% at the requested confidence level.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm


def _clean_returns(returns: pd.Series) -> pd.Series:
    """Return finite numeric observations without changing the original series."""
    cleaned = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(cleaned) < 2:
        raise ValueError("At least two finite return observations are required.")
    return cleaned.astype(float)


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Estimate one-period historical VaR as a positive loss threshold."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    series = _clean_returns(returns)
    return float(max(0.0, -np.quantile(series.to_numpy(), 1.0 - confidence)))


def parametric_var(returns: pd.Series, confidence: float = 0.95, mean: float | None = None) -> float:
    """Estimate normal-distribution VaR from sample mean and standard deviation."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    series = _clean_returns(returns)
    mu = float(series.mean() if mean is None else mean)
    sigma = float(series.std(ddof=1))
    if sigma == 0.0:
        return float(max(0.0, -mu))
    quantile = mu + sigma * float(norm.ppf(1.0 - confidence))
    return float(max(0.0, -quantile))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """Estimate historical expected shortfall (CVaR) as an average tail loss."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    series = _clean_returns(returns)
    cutoff = float(np.quantile(series.to_numpy(), 1.0 - confidence))
    tail = series[series <= cutoff]
    if tail.empty:
        return historical_var(series, confidence)
    return float(max(0.0, -tail.mean()))


def garch_var(
    returns: pd.Series,
    confidence: float = 0.95,
    p: int = 1,
    q: int = 1,
    dist: str = "normal",
) -> dict[str, Any]:
    """Fit a local GARCH model and return conditional volatility and VaR.

    Returns model metadata rather than the fitted model object so results remain
    easy to serialize into DataSense reports. Returns are scaled to percentage
    points for numerical stability and converted back before reporting VaR.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if p < 1 or q < 1:
        raise ValueError("p and q must be positive")
    series = _clean_returns(returns)
    if len(series) < 30:
        raise ValueError("At least 30 return observations are recommended for GARCH estimation.")

    try:
        from arch import arch_model
    except ImportError as exc:  # pragma: no cover - dependency is declared in requirements
        raise RuntimeError("The 'arch' package is required for GARCH VaR.") from exc

    scaled = series * 100.0
    model = arch_model(scaled, mean="Constant", vol="GARCH", p=p, q=q, dist=dist, rescale=False)
    fitted = model.fit(disp="off", show_warning=False)
    forecast = fitted.forecast(horizon=1, reindex=False)
    variance_pct2 = float(forecast.variance.iloc[-1, 0])
    sigma = float(np.sqrt(max(variance_pct2, 0.0)) / 100.0)
    mu = float(fitted.params.get("mu", 0.0) / 100.0)

    if dist == "normal":
        tail_quantile = float(norm.ppf(1.0 - confidence))
    else:
        # Keep the public API conservative: non-normal distributions should be
        # extended explicitly rather than silently applying the wrong quantile.
        raise ValueError("garch_var currently supports dist='normal' only.")

    var = float(max(0.0, -(mu + sigma * tail_quantile)))
    return {
        "var": var,
        "conditional_volatility": sigma,
        "mean_return": mu,
        "confidence": confidence,
        "p": p,
        "q": q,
        "distribution": dist,
        "n_obs": int(len(series)),
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
    }
