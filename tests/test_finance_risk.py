import numpy as np
import pandas as pd
import pytest

from core.finance import expected_shortfall, historical_var, parametric_var


def test_historical_var_returns_positive_tail_loss() -> None:
    returns = pd.Series([-0.10, -0.04, -0.02, 0.01, 0.03, 0.05])
    expected = -np.quantile(returns.to_numpy(), 0.05)
    assert historical_var(returns, confidence=0.95) == pytest.approx(expected)


def test_parametric_var_handles_constant_returns() -> None:
    returns = pd.Series([0.01] * 10)
    assert parametric_var(returns, confidence=0.95) == 0.0


def test_expected_shortfall_is_at_least_historical_var() -> None:
    returns = pd.Series([-0.12, -0.08, -0.03, -0.01, 0.01, 0.02, 0.04])
    var = historical_var(returns, confidence=0.80)
    es = expected_shortfall(returns, confidence=0.80)
    assert es >= var


def test_risk_functions_drop_non_finite_values() -> None:
    returns = pd.Series([-0.02, np.nan, np.inf, -0.01, 0.02])
    assert historical_var(returns, confidence=0.95) >= 0.0


@pytest.mark.parametrize("confidence", [0.0, 1.0, -0.1, 1.1])
def test_var_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError):
        historical_var(pd.Series([-0.01, 0.01]), confidence)
