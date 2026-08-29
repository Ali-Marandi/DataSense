"""Factor helper functions for DataSense finance features."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from typing import Dict


def _to_returns(prices: pd.Series) -> pd.Series:
    """Convert a price series to returns. Prefer log returns unless non-positive values exist.

    Drops NA results from the differencing.
    """
    prices = prices.dropna()
    if (prices <= 0).any():
        return prices.pct_change().dropna()
    return np.log(prices).diff().dropna()


def compute_beta(asset_prices: pd.Series, market_prices: pd.Series) -> Dict:
    """
    Compute CAPM beta and simple regression diagnostics.

    Parameters
    - asset_prices: price series (indexed by date) for the asset
    - market_prices: price series (indexed by date) for the market benchmark

    Returns a dict with keys: beta, alpha, r2, n_obs, asset_returns, market_returns
    """
    asset = _to_returns(asset_prices).rename("asset")
    market = _to_returns(market_prices).rename("market")

    df = pd.concat([asset, market], axis=1).dropna()
    if df.shape[0] < 2:
        raise ValueError("Not enough overlapping observations to compute beta.")

    X = sm.add_constant(df["market"])  # intercept + market
    model = sm.OLS(df["asset"], X).fit()

    return {
        "beta": float(model.params["market"]),
        "alpha": float(model.params["const"]),
        "r2": float(model.rsquared),
        "n_obs": int(model.nobs),
        "asset_returns": df["asset"],
        "market_returns": df["market"],
    }


def fama_french_3factor(asset_returns: pd.Series, factors_df: pd.DataFrame) -> Dict:
    """
    Simple Fama-French 3-factor regression.

    asset_returns: series of excess returns (asset - rf) indexed by date
    factors_df: DataFrame with columns ['MKT', 'SMB', 'HML'] (already excess)
    """
    required = ["MKT", "SMB", "HML"]
    if not all(c in factors_df.columns for c in required):
        raise ValueError(f"factors_df must contain columns: {required}")

    df = pd.concat([asset_returns, factors_df[required]], axis=1).dropna()
    if df.shape[0] < 5:
        raise ValueError("Not enough observations for Fama-French regression.")

    y = df.iloc[:, 0]
    X = sm.add_constant(df.iloc[:, 1:])
    res = sm.OLS(y, X).fit()

    return {
        "params": res.params.to_dict(),
        "r2": float(res.rsquared),
        "n_obs": int(res.nobs),
        "summary": res.summary().as_text(),
    }
