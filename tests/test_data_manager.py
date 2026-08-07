import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    assert manager.df is not None
    assert list(manager.df.columns) == ["a", "b", "group"]

def test_clean_data(manager):
    # Add a duplicate
    manager.df = pd.concat([manager.df, manager.df.iloc[[0]]]).reset_index(drop=True)
    initial_len = len(manager.df)
    success, _ = manager.clean_data(drop_duplicates=True)
    assert success
    assert len(manager.df) == initial_len - 1
