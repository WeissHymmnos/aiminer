import unittest
import pandas as pd
import numpy as np

import pytest

pl = pytest.importorskip("polars", reason="Polars tests require the optional native engine stack")

from core.alphaeval.polars_engine import PolarsEngine


pytestmark = pytest.mark.native


class TestPolarsOperatorsExtensive(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2020-01-01", periods=20)
        instruments = ["A", "B", "C"]
        index = pd.MultiIndex.from_product(
            [dates, instruments], names=["datetime", "instrument"]
        )
        data = np.random.randn(len(index), 2)
        # Add some specific patterns
        self.df = pd.DataFrame(
            data, index=index, columns=["close", "volume"]
        ).sort_index()
        # Ensure some predictable values
        self.df.loc[("2020-01-01", "A"), "close"] = 10.0
        self.df.loc[("2020-01-02", "A"), "close"] = 11.0
        self.df.loc[("2020-01-01", "B"), "close"] = 20.0
        self.df.loc[("2020-01-02", "B"), "close"] = 19.0

    def get_result(self, expr):
        pl_df = pl.from_pandas(self.df.reset_index())
        # Sorting MUST be instrument first for rolling time-series ops to work correctly
        pl_df = pl_df.sort(["instrument", "datetime"])
        # PolarsEngine handles datetime string conversion if needed
        pl_df = pl_df.with_columns(pl.col("datetime").dt.to_string("%Y-%m-%d"))
        engine = PolarsEngine(pl_df)
        # Use compute_all for proper two-step materialization of nested expressions
        result = engine.compute_all(pl_df, [expr])
        return result.rename({expr: "factor"})

    def test_rolling_ops(self):
        # Mean, Sum, Std, Delta, Ref
        res = self.get_result("Mean($close, 2)")
        a_vals = (
            res.filter(pl.col("instrument") == "A").sort("datetime")["factor"].to_list()
        )
        self.assertAlmostEqual(a_vals[1], 10.5)

        res = self.get_result("Sum($close, 2)")
        a_vals = (
            res.filter(pl.col("instrument") == "A").sort("datetime")["factor"].to_list()
        )
        self.assertAlmostEqual(a_vals[1], 21.0)

        res = self.get_result("Delta($close, 1)")
        a_vals = (
            res.filter(pl.col("instrument") == "A").sort("datetime")["factor"].to_list()
        )
        self.assertAlmostEqual(a_vals[1], 1.0)

        res = self.get_result("Ref($close, 1)")
        a_vals = (
            res.filter(pl.col("instrument") == "A").sort("datetime")["factor"].to_list()
        )
        self.assertEqual(a_vals[1], 10.0)

    def test_cross_sectional_ops(self):
        # Rank, CSRank, CSZScore
        res = self.get_result("Rank($close)")
        # On 2020-01-01: A=10, B=20, C=rand.
        # Rank should be between 0 and 1
        d1 = res.filter(pl.col("datetime") == "2020-01-01").sort("instrument")
        ranks = d1["factor"].to_list()
        self.assertTrue(all(0 <= r <= 1 for r in ranks))
        # A < B on d1
        self.assertTrue(ranks[0] < ranks[1])

    def test_logical_and_conditional(self):
        res = self.get_result("If($close > 15, pl.lit(1), pl.lit(0))")
        d1 = res.filter(pl.col("datetime") == "2020-01-01").sort("instrument")
        vals = d1["factor"].to_list()
        self.assertEqual(vals[0], 0)  # A=10
        self.assertEqual(vals[1], 1)  # B=20

    def test_ts_ops_slow(self):
        # Ts_Rank, Ts_ArgMax
        res = self.get_result("Ts_Rank($close, 5)")
        a_vals = (
            res.filter(pl.col("instrument") == "A").sort("datetime")["factor"].to_list()
        )
        # Just check it runs and produces values for indices >= 4
        self.assertIsNotNone(a_vals[10])
        self.assertTrue(0 <= a_vals[10] <= 1)

    def test_complex_nesting(self):
        # Mean only
        res = self.get_result("Mean($close, 5)")
        print("Mean only:\n", res.head(5))
        # Rank of Mean
        res = self.get_result("Rank(Mean($close, 5))")
        print("Rank of Mean:\n", res.head(5))
        self.assertIsNotNone(res["factor"][10])

    def test_infix_operators(self):
        # Test $close + $volume * 2
        res = self.get_result("$close + $volume * 2")
        self.assertAlmostEqual(res["factor"][0], res["close"][0] + res["volume"][0] * 2)

    def test_logical_operators(self):
        # Test $close > $volume
        res = self.get_result("$close > $volume")
        # In PolarsEngine, Greater returns a boolean-like column
        self.assertIsNotNone(res["factor"][0])

    def test_ts_rank_with_underscore(self):
        # Test Ts_Rank which failed before
        res = self.get_result("Ts_Rank($close, 5)")
        self.assertIsNotNone(res["factor"][10])

    def test_math_ops(self):
        res = self.get_result("Add($close, $volume)")
        self.assertAlmostEqual(res["factor"][0], res["close"][0] + res["volume"][0])

        res = self.get_result("Mul(Log(Abs($close) + 1), 2)")
        self.assertIsNotNone(res["factor"][0])


if __name__ == "__main__":
    unittest.main()
