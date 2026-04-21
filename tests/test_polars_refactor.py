import unittest
import pandas as pd
import numpy as np

import pytest

pl = pytest.importorskip("polars", reason="Polars tests require the optional native engine stack")
pytest.importorskip("rqdatac", reason="RiceQuant evaluator imports the optional rqdatac client")

from core.alphaeval.rq_eval import RiceQuantEval
from core.alphaeval.polars_engine import PolarsEngine


pytestmark = pytest.mark.native


class TestPolarsRefactor(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        dates = pd.date_range("2020-01-01", periods=10)
        instruments = ["000001.XSHE", "000002.XSHE"]

        # Create a MultiIndex DataFrame
        index = pd.MultiIndex.from_product(
            [dates, instruments], names=["datetime", "instrument"]
        )
        data = np.random.randn(len(index), 3)
        self.df = pd.DataFrame(
            data, index=index, columns=["close", "volume", "open"]
        ).sort_index()

        # Mock evaluator
        # Note: RiceQuantEval calls init_rq_auth in __init__, which might fail if no creds
        # We might need to mock init_rq_auth or use a dummy class

    def test_polars_engine_basic(self):
        pl_df = pl.from_pandas(self.df.reset_index())
        # Convert datetime to string for PolarsEngine
        pl_df = pl_df.with_columns(pl.col("datetime").cast(pl.String))

        engine = PolarsEngine(pl_df)
        expr = engine.evaluate("Mean($close, 2)")
        res = pl_df.with_columns(factor=expr)

        # Verify A's rolling mean
        a_data = res.filter(pl.col("instrument") == "000001.XSHE").sort("datetime")
        close_vals = a_data["close"].to_list()
        factor_vals = a_data["factor"].to_list()

        self.assertAlmostEqual(
            factor_vals[1], (close_vals[0] + close_vals[1]) / 2, places=5
        )
        self.assertTrue(factor_vals[0] is None or np.isnan(float(factor_vals[0])))

    def test_ricequant_eval_integration(self):
        # We need to bypass the auth in RiceQuantEval for testing
        import core.alphaeval.rq_eval as rq_eval

        original_auth = rq_eval.init_rq_auth
        rq_eval.init_rq_auth = lambda: None

        try:
            evaluator = RiceQuantEval(
                factor_expressions=["Mean($close, 5)", "Rank($close)"],
                test_start_date="2020-01-01",
                test_end_date="2020-01-10",
            )
            evaluator.raw_data = self.df
            evaluator.compute_factors()

            self.assertIsNotNone(evaluator.factor_data)
            self.assertEqual(len(evaluator.factor_data.columns), 2)
            self.assertTrue("Mean($close, 5)" in evaluator.factor_data.columns)

        finally:
            rq_eval.init_rq_auth = original_auth

    def test_ricequant_eval_integration_polars(self):
        # We need to bypass the auth in RiceQuantEval for testing
        import core.alphaeval.rq_eval as rq_eval

        original_auth = rq_eval.init_rq_auth
        rq_eval.init_rq_auth = lambda: None

        try:
            evaluator = RiceQuantEval(
                factor_expressions=["Mean($close, 5)", "Rank($close)"],
                test_start_date="2020-01-01",
                test_end_date="2020-01-10",
                engine="polars",
            )
            evaluator.raw_data = self.df
            evaluator.compute_factors()

            self.assertIsNotNone(evaluator.factor_data)
            self.assertEqual(len(evaluator.factor_data.columns), 2)
            self.assertTrue("Mean($close, 5)" in evaluator.factor_data.columns)
            self.assertTrue("Rank($close)" in evaluator.factor_data.columns)

            # Check for a specific value
            a_data = evaluator.factor_data.loc[(slice(None), "000001.XSHE"), :]
            self.assertFalse(a_data.empty)

        finally:
            rq_eval.init_rq_auth = original_auth


if __name__ == "__main__":
    unittest.main()
