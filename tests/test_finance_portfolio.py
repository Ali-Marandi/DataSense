import numpy as np
import pandas as pd
import pytest

from core.finance.portfolio import (
    annualized_volatility,
    max_drawdown,
    portfolio_returns,
    risk_summary,
    sharpe_ratio,
    sortino_ratio,
)


def test_portfolio_returns_aligns_and_preserves_index():
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    frame = pd.DataFrame(
        {
            "a": [0.01, 0.02, np.nan, 0.00],
            "b": [0.00, 0.01, 0.02, 0.03],
        },
        index=index,
    )

    result = portfolio_returns(frame, {"a": 0.6, "b": 0.4})

    assert list(result.index) == [index[0], index[1], index[3]]
    assert result.iloc[0] == pytest.approx(0.006)
    assert result.name == "portfolio"


def test_portfolio_weights_must_sum_to_one():
    frame = pd.DataFrame({"a": [0.01, 0.02], "b": [0.00, 0.01]})
    with pytest.raises(ValueError, match="sum to 1.0"):
        portfolio_returns(frame, {"a": 0.5, "b": 0.6})


def test_max_drawdown_is_positive_peak_to_trough_loss():
    returns = pd.Series([0.10, 0.00, -0.20, 0.05])
    assert max_drawdown(returns) == pytest.approx(0.20, abs=1e-12)


def test_sharpe_and_sortino_are_finite_for_variable_returns():
    returns = pd.Series([0.01, -0.005, 0.02, 0.0, 0.015])
    assert np.isfinite(sharpe_ratio(returns))
    assert np.isfinite(sortino_ratio(returns))
    assert annualized_volatility(returns) > 0


def test_risk_summary_is_serializable_and_complete():
    returns = pd.Series([0.01, -0.005, 0.02, 0.0, 0.015, -0.01])
    summary = risk_summary(returns, confidence=0.95, periods_per_year=252)

    assert summary["observations"] == 6
    assert summary["confidence"] == 0.95
    assert summary["periods_per_year"] == 252
    for key in (
        "annualized_volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "historical_var",
        "parametric_var",
        "expected_shortfall",
    ):
        assert key in summary
