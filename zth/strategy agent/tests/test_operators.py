import unittest
import pandas as pd
import numpy as np


class TestOperators(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2020-01-01", periods=5)
        self.instruments = ["000001.XSHE", "000002.XSHE", "000063.XSHE"]
        data = np.array([
            [10.0, 20.0, 30.0],
            [11.0, 19.0, 31.0],
            [12.0, 18.0, 32.0],
            [13.0, 17.0, 33.0],
            [14.0, 16.0, 34.0],
        ])
        self.df = pd.DataFrame(data, index=self.dates, columns=self.instruments)

    def test_mean(self):
        def _get_op_context():
            def _get_n(n):
                return int(n)

            return {
                "Mean": lambda df, n: df.rolling(_get_n(n)).mean(),
                "Rank": lambda df: df.rank(axis=1, pct=True),
                "Abs": lambda df: np.abs(df),
            }

        ctx = _get_op_context()
        res = ctx["Mean"](self.df, 2)
        self.assertEqual(res.iloc[1, 0], 10.5)
        self.assertTrue(np.isnan(res.iloc[0, 0]))

    def test_cs_rank(self):
        res = self.df.rank(axis=1, pct=True)
        self.assertAlmostEqual(res.iloc[0, 0], 0.3333333, places=5)
        self.assertAlmostEqual(res.iloc[0, 2], 1.0, places=5)

    def test_zscore_robustness(self):
        from core.alphaeval.rq_eval import zscore

        empty_df = pd.DataFrame(0, index=self.dates, columns=self.instruments)
        res = zscore(empty_df)
        self.assertFalse(res.isnull().values.any())
        self.assertEqual(res.values.sum(), 0)


if __name__ == "__main__":
    unittest.main()
