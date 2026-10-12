import unittest

import pandas as pd

from manager import PortfolioManager


class TestManagerCorrelation(unittest.TestCase):
    def test_redundant_factor_detection(self):
        dates = pd.date_range("2020-01-01", periods=30)
        s1 = pd.Series(range(30), index=dates, dtype=float)
        # Highly correlated series
        s2 = s1 * 1.5 + 2.0
        # Uncorrelated series
        s3 = pd.Series([(-1) ** i for i in range(30)], index=dates, dtype=float)

        pool = [{"id": "alpha_1", "returns": s1}]

        is_red_1, corr_1 = PortfolioManager._is_redundant_factor(s2, pool, max_corr=0.7)
        self.assertTrue(is_red_1)
        self.assertIsNotNone(corr_1)
        self.assertGreater(corr_1, 0.99)

        is_red_2, corr_2 = PortfolioManager._is_redundant_factor(s3, pool, max_corr=0.7)
        self.assertFalse(is_red_2)


if __name__ == "__main__":
    unittest.main()
