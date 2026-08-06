import unittest
import pandas as pd
import os
import sys

# Add the parent directory to sys.path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_manager import DataManager

class TestDataManager(unittest.TestCase):
    def setUp(self):
        self.manager = DataManager()
        self.test_file = "test_data.csv"
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        df.to_csv(self.test_file, index=False)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_load_data(self):
        success, message = self.manager.load_data(self.test_file)
        self.assertTrue(success)
        self.assertIsNotNone(self.manager.df)
        self.assertEqual(len(self.manager.df), 3)

    def test_get_columns(self):
        self.manager.load_data(self.test_file)
        cols = self.manager.get_columns()
        self.assertIn('A', cols)
        self.assertIn('B', cols)

    def test_get_summary(self):
        self.manager.load_data(self.test_file)
        summary = self.manager.get_summary()
        self.assertIsNotNone(summary)

    def test_clean_data(self):
        self.manager.load_data(self.test_file)
        # Add a duplicate
        self.manager.df = pd.concat([self.manager.df, self.manager.df.iloc[[0]]])
        success, _ = self.manager.clean_data(drop_duplicates=True)
        self.assertTrue(success)
        self.assertEqual(len(self.manager.df), 3)

if __name__ == "__main__":
    unittest.main()
