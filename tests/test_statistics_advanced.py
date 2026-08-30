import numpy as np
import pandas as pd
import pytest

from core import statistics as st


def test_t_test_reports_effect_size_and_confidence_interval() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [0, 1, 2, 3, 4]})
    result = st.t_test(frame, "a", "b")
    assert result["effect_size_cohens_d"] > 0
    assert result["difference_ci_low"] < result["mean_difference"] < result["difference_ci_high"]


def test_paired_t_test_reports_standardized_effect() -> None:
    frame = pd.DataFrame({"before": [10, 11, 12, 13, 14], "after": [9, 10, 11, 12, 13]})
    result = st.t_test(frame, "before", "after", paired=True)
    assert result["effect_size_cohens_d"] == pytest.approx(1.0)
    assert result["n"] == 5


def test_anova_reports_eta_squared() -> None:
    frame = pd.DataFrame({"value": [1, 2, 3, 10, 11, 12], "group": ["A", "A", "A", "B", "B", "B"]})
    result = st.anova(frame, "value", "group")
    assert 0.0 <= result["eta_squared"] <= 1.0
    assert result["groups"] == 2


def test_chi_square_reports_cramers_v() -> None:
    frame = pd.DataFrame({"a": ["x", "x", "y", "y"], "b": ["u", "v", "u", "v"]})
    result = st.chi_square(frame, "a", "b")
    assert 0.0 <= result["cramers_v"] <= 1.0


def test_multiple_testing_adjustments_are_bounded_and_monotone() -> None:
    p = np.array([0.001, 0.02, 0.04, 0.5])
    for method in ("bonferroni", "holm", "fdr_bh"):
        adjusted = st.adjust_pvalues(p, method)
        assert np.all(adjusted >= p)
        assert np.all((0 <= adjusted) & (adjusted <= 1))
        assert adjusted[0] <= adjusted[-1]


def test_bootstrap_ci_is_deterministic() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    ci1 = st._bootstrap_ci(values, np.mean, seed=42)
    ci2 = st._bootstrap_ci(values, np.mean, seed=42)
    assert ci1 == ci2
