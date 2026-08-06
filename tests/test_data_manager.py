import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ml, statistics as st
from core.data_manager import DataManager


@pytest.fixture()
def manager(tmp_path):
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "a": rng.normal(10, 2, 120),
            "b": rng.normal(4, 1, 120),
            "group": rng.choice(["x", "y", "z"], 120),
        }
    )
    frame.loc[:4, "a"] = np.nan
    path = tmp_path / "data.csv"
    frame.to_csv(path, index=False)
    m = DataManager()
    ok, _ = m.load(str(path))
    assert ok
    return m


def test_load_and_profile(manager):
    assert manager.loaded
    assert manager.numeric_columns() == ["a", "b"]
    profile = manager.profile()
    assert set(profile["Column"]) == {"a", "b", "group"}
    assert profile.loc[profile["Column"] == "a", "Missing"].iloc[0] == 5


def test_fill_and_history(manager):
    manager.fill_missing(["a"], "mean")
    assert manager.df["a"].isna().sum() == 0
    assert manager.can_undo
    manager.undo()
    assert manager.df["a"].isna().sum() == 5
    manager.redo()
    assert manager.df["a"].isna().sum() == 0


def test_transformations(manager):
    manager.add_computed_column("ratio", "a / b")
    assert "ratio" in manager.columns()
    manager.scale_columns(["b"], "minmax")
    assert manager.df["b"].max() <= 1.0001
    removed = manager.drop_duplicates()
    assert removed >= 0
    ok, _ = manager.query("b > 0")
    assert ok


def test_export_roundtrip(manager, tmp_path):
    out = tmp_path / "out.csv"
    ok, _ = manager.export(str(out))
    assert ok and out.exists()


def test_statistics(manager):
    manager.fill_missing(["a"], "mean")
    assert not st.describe(manager.df, ["a", "b"]).empty
    assert st.correlation(manager.df, ["a", "b"]).shape == (2, 2)
    assert "p_value" in st.anova(manager.df, "a", "group")
    assert "r_squared" in st.linear_regression(manager.df, "a", ["b"])


def test_machine_learning(manager):
    manager.fill_missing(["a"], "mean")
    result = ml.train_regression(manager.df, "a", ["b"], "Linear Regression")
    assert "R2 (test)" in result.metrics
    clusters = ml.run_clustering(manager.df, ["a", "b"], 3)
    assert clusters.predictions is not None
