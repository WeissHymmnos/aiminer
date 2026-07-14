import unittest
from unittest.mock import patch

import pandas as pd

from aiminer.core import manual_runner


class FakeEvaluator:
    def __init__(self, factor_expressions, test_start_date, test_end_date, market, daily_normalize, engine):
        self.factor_expressions = factor_expressions
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self.market = market
        self.daily_normalize = daily_normalize
        self.engine = engine

    @staticmethod
    def dry_run(expression):
        return True, "ok"

    def fetch_data(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        self.factor_data = pd.DataFrame(
            {
                self.factor_expressions[0]: [0.1, 0.9, 0.2, 0.8, 0.3],
            },
            index=pd.MultiIndex.from_product([dates, ["A"]], names=["datetime", "instrument"]),
        )
        self.label_data = pd.DataFrame(
            {"label": [0.01, 0.02, -0.01, 0.03, 0.00]},
            index=self.factor_data.index,
        )

    def compute_factors(self):
        return None


class TestManualStrategyRunner(unittest.TestCase):
    @patch("aiminer.core.manual_runner.validate_expression", return_value=(True, "ok"))
    @patch("aiminer.core.evaluator_factory.build_evaluator")
    def test_run_manual_strategy_backtest_returns_payload(self, mock_build_evaluator, _mock_validate):
        evaluator = FakeEvaluator(
            factor_expressions=["Rank($close)"],
            test_start_date="2024-01-01",
            test_end_date="2024-01-05",
            market="LOCAL",
            daily_normalize=True,
            engine="pandas",
        )
        evaluator.fetch_data()
        mock_build_evaluator.return_value = evaluator
        payload = manual_runner.run_manual_strategy_backtest(
            "Rank($close)",
            {
                "label": "test",
                "strategy_mode": "time_series",
                "signal_source": "expression",
                "direction": "long_flat",
                "selection_rule": "threshold",
                "long_threshold": 0.5,
                "exit_threshold": 0.4,
                "start_date": "2024-01-01",
                "end_date": "2024-01-05",
                "engine": "pandas",
            },
            data_backend="local",
            market_profile="cn_stock",
            local_data_path="/tmp/local-data",
        )
        self.assertEqual(payload["run_type"], "strategy_backtest")
        self.assertIn("metrics", payload)
        self.assertIn("daily_returns", payload)
