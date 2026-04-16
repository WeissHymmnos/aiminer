import unittest
import pandas as pd
import numpy as np
from core.alphaeval.rq_eval import RiceQuantEval
from loguru import logger


class TestNumericalConsistency(unittest.TestCase):
    def setUp(self):
        # Create a more complex dummy dataset
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=30)
        instruments = [f"S{i:02d}" for i in range(20)]

        index = pd.MultiIndex.from_product(
            [dates, instruments], names=["datetime", "instrument"]
        )
        data = np.random.randn(len(index), 3)
        self.df = pd.DataFrame(
            data, index=index, columns=["close", "volume", "open"]
        ).sort_index()
        # Add some NaNs to test robustness
        self.df.iloc[10, 0] = np.nan
        self.df.iloc[50, 1] = np.nan

    def compare_expr(self, expr):
        # 1. Pandas Run
        eval_pd = RiceQuantEval(
            factor_expressions=[expr],
            test_start_date="2020-01-01",
            test_end_date="2020-01-30",
            engine="pandas",
            daily_normalize=False,  # Compare raw values first
        )
        eval_pd.raw_data = self.df
        eval_pd.compute_factors()
        res_pd = eval_pd.factor_data[expr]

        # 2. Polars Run
        eval_pl = RiceQuantEval(
            factor_expressions=[expr],
            test_start_date="2020-01-01",
            test_end_date="2020-01-30",
            engine="polars",
            daily_normalize=False,
        )
        eval_pl.raw_data = self.df
        eval_pl.compute_factors()
        res_pl = eval_pl.factor_data[expr]

        # Compare
        # Note: Polars might use different names for the index, let's align
        res_pl.index = res_pd.index

        # Fill NaN for comparison if needed, or check where both are NaN
        # Polars might return None/NaN differently
        pd_vals = res_pd.values
        pl_vals = res_pl.values

        # Use np.allclose but handle NaNs
        mask = ~np.isnan(pd_vals) & ~np.isnan(pl_vals)
        if not np.any(mask):
            logger.warning(f"No non-NaN values for {expr}")
            return

        diff = np.abs(pd_vals[mask] - pl_vals[mask])
        max_diff = np.max(diff)

        logger.info(f"Expr: {expr} | Max Diff: {max_diff}")
        self.assertLess(max_diff, 1e-6, f"Mismatch in {expr}")

    def test_basic_ops(self):
        self.compare_expr("Add($close, $volume)")
        self.compare_expr("Mul($close, 2)")
        self.compare_expr("Greater($close, $open)")

    def test_rolling_ops(self):
        self.compare_expr("Mean($close, 5)")
        self.compare_expr("Sum($volume, 10)")
        self.compare_expr("Ref($close, 1)")

    def test_cross_sectional_ops(self):
        self.compare_expr("Rank($close)")
        self.compare_expr("CSRank($close)")
        self.compare_expr("CSZScore($close)")

    def test_custom_ops(self):
        # These use the Rust plugin
        self.compare_expr("Ts_Rank($close, 10)")
        # Ts_ArgMax might return slightly different if multiple max values exist, but let's try
        self.compare_expr("Ts_ArgMax($close, 5)")

    def test_nested_ops(self):
        # Nesting cross-sectional over time-series
        self.compare_expr("Rank(Mean($close, 5))")


if __name__ == "__main__":
    unittest.main()
