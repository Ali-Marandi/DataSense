"""Time-series resampling, decomposition and forecasting."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MODELS = ["Holt-Winters", "Exponential Smoothing", "Linear Trend", "Naive Seasonal"]
FREQUENCIES = {
    "Hourly": "h", "Daily": "D", "Weekly": "W", "Monthly": "MS", "Quarterly": "QS", "Yearly": "YS",
}


@dataclass
class ForecastResult:
    history: pd.Series
    forecast: pd.Series
    lower: pd.Series | None
    upper: pd.Series | None
    model: str
    metrics: dict[str, str]


def build_series(
    df: pd.DataFrame, date_column: str, value_column: str,
    freq: str = "D", agg: str = "sum",
) -> pd.Series:
    frame = df[[date_column, value_column]].copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna()
    if frame.empty:
        raise ValueError("No valid date/value pairs found.")
    series = frame.set_index(date_column)[value_column].sort_index()
    series = series.resample(freq).agg(agg)
    return series.interpolate().dropna()


def decompose(series: pd.Series, period: int | None = None) -> pd.DataFrame:
    from statsmodels.tsa.seasonal import seasonal_decompose

    if period is None:
        period = _guess_period(series)
    if len(series) < 2 * period:
        raise ValueError(f"Need at least {2 * period} points to decompose with period {period}.")
    result = seasonal_decompose(series, model="additive", period=period)
    return pd.DataFrame(
        {
            "observed": result.observed,
            "trend": result.trend,
            "seasonal": result.seasonal,
            "residual": result.resid,
        }
    )


def _guess_period(series: pd.Series) -> int:
    freq = getattr(series.index, "freqstr", None) or ""
    freq = freq.upper()
    if freq.startswith("H"):
        return 24
    if freq.startswith("D"):
        return 7
    if freq.startswith("W"):
        return 52
    if freq.startswith("M"):
        return 12
    if freq.startswith("Q"):
        return 4
    return max(2, min(12, len(series) // 4 or 2))


def _metrics(actual: pd.Series, fitted: pd.Series) -> dict[str, str]:
    joined = pd.concat([actual, fitted], axis=1).dropna()
    if joined.shape[0] < 2:
        return {"MAE": "n/a", "RMSE": "n/a", "MAPE": "n/a"}
    a = joined.iloc[:, 0].to_numpy(dtype=float)
    f = joined.iloc[:, 1].to_numpy(dtype=float)
    mae = float(np.mean(np.abs(a - f)))
    rmse = float(np.sqrt(np.mean((a - f) ** 2)))
    with np.errstate(divide="ignore", invalid="ignore"):
        mape_arr = np.abs((a - f) / np.where(a == 0, np.nan, a))
    mape = float(np.nanmean(mape_arr)) * 100 if np.isfinite(np.nanmean(mape_arr)) else np.nan
    return {
        "MAE": f"{mae:,.4f}",
        "RMSE": f"{rmse:,.4f}",
        "MAPE": f"{mape:.2f}%" if np.isfinite(mape) else "n/a",
    }


def forecast(series: pd.Series, periods: int = 12, model: str = "Holt-Winters") -> ForecastResult:
    if len(series) < 5:
        raise ValueError("At least 5 observations are required to forecast.")
    index = pd.date_range(
        series.index[-1], periods=periods + 1,
        freq=series.index.freq or pd.infer_freq(series.index) or "D",
    )[1:]

    lower = upper = None
    if model == "Linear Trend":
        x = np.arange(len(series), dtype=float)
        slope, intercept = np.polyfit(x, series.to_numpy(dtype=float), 1)
        fitted = pd.Series(intercept + slope * x, index=series.index)
        future = intercept + slope * np.arange(len(series), len(series) + periods, dtype=float)
        values = pd.Series(future, index=index)
        residual_std = float((series - fitted).std(ddof=1) or 0)
        lower = values - 1.96 * residual_std
        upper = values + 1.96 * residual_std
    elif model == "Naive Seasonal":
        period = _guess_period(series)
        tail = series.iloc[-period:].to_numpy(dtype=float)
        reps = int(np.ceil(periods / len(tail)))
        values = pd.Series(np.tile(tail, reps)[:periods], index=index)
        fitted = series.shift(period)
    else:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        period = _guess_period(series)
        seasonal = "add" if model == "Holt-Winters" and len(series) >= 2 * period else None
        fit = ExponentialSmoothing(
            series, trend="add", seasonal=seasonal,
            seasonal_periods=period if seasonal else None,
            initialization_method="estimated",
        ).fit()
        values = pd.Series(np.asarray(fit.forecast(periods)), index=index)
        fitted = pd.Series(np.asarray(fit.fittedvalues), index=series.index)
        residual_std = float((series - fitted).std(ddof=1) or 0)
        lower = values - 1.96 * residual_std
        upper = values + 1.96 * residual_std

    return ForecastResult(series, values, lower, upper, model, _metrics(series, fitted))


def forecast_frame(result: ForecastResult) -> pd.DataFrame:
    data = {"forecast": result.forecast}
    if result.lower is not None:
        data["lower_95"] = result.lower
    if result.upper is not None:
        data["upper_95"] = result.upper
    frame = pd.DataFrame(data)
    frame.index.name = "period"
    return frame.reset_index()
