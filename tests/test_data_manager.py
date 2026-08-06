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


    def test_clean_data(self):
        self.manager.load_data(self.test_file)
        # Add a duplicate
        self.manager.df = pd.concat([self.manager.df, self.manager.df.iloc[[0]]])
        success, _ = self.manager.clean_data(drop_duplicates=True)
        self.assertTrue(success)
        self.assertEqual(len(self.manager.df), 3)

if __name__ == "__main__":
    unittest.main()
