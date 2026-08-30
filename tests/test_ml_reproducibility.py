import numpy as np
import pandas as pd

from core.ml import dataset_fingerprint, detect_leakage_risks, train_regression


def test_dataset_fingerprint_is_stable_and_value_agnostic() -> None:
    a = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    b = pd.DataFrame({"x": [9, 8], "y": [7, 6]})
    assert dataset_fingerprint(a, "y", ["x"]) == dataset_fingerprint(b, "y", ["x"])


def test_leakage_detector_flags_obvious_post_target_feature() -> None:
    frame = pd.DataFrame({"revenue": [1, 2], "revenue_post_outcome": [3, 4]})
    warnings = detect_leakage_risks(frame, "revenue", ["revenue_post_outcome"])
    assert warnings


def test_time_aware_regression_uses_chronological_split() -> None:
    rows = 30
    frame = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=rows, freq="D"),
        "x": np.arange(rows, dtype=float),
        "y": np.arange(rows, dtype=float) * 2.0,
    })
    result = train_regression(frame, "y", ["x"], "Linear Regression", time_column="time")
    assert result.metadata["split_strategy"] == "chronological"
    assert result.metadata["random_state"] == 42
    assert result.metadata["dataset_fingerprint"]
