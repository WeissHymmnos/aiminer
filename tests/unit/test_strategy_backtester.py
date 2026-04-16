import unittest

import pandas as pd

from core.strategy import StrategyBacktester, StrategyConfig


class TestStrategyBacktester(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2024-01-01", periods=6, freq="D")
        self.signal_df = pd.DataFrame(
            {
                "A": [0.1, 0.9, 0.8, 0.2, 0.7, 0.6],
                "B": [0.2, 0.1, 0.3, 0.7, 0.4, 0.5],
                "C": [0.9, 0.3, 0.2, 0.1, 0.2, 0.4],
            },
            index=self.dates,
        )
        self.label_df = pd.DataFrame(
            {
                "A": [0.01, 0.02, -0.01, 0.00, 0.03, 0.01],
                "B": [0.00, -0.01, 0.01, 0.02, -0.01, 0.02],
                "C": [0.02, 0.01, 0.00, -0.02, 0.01, -0.01],
            },
            index=self.dates,
        )

    def test_cross_sectional_long_short_runs(self):
        cfg = StrategyConfig(
            strategy_mode="cross_sectional",
            signal_source="expression",
            direction="long_short",
            selection_rule="top_bottom_n",
            top_n=1,
            bottom_n=1,
            max_weight_per_position=0.5,
        )
        result = StrategyBacktester(cfg).run(self.signal_df, self.label_df)
        self.assertIn("metrics", result)
        self.assertEqual(len(result["daily_returns"]), len(self.dates))
        self.assertIn("turnover", result["metrics"])

    def test_time_series_long_flat_runs(self):
        cfg = StrategyConfig(
            strategy_mode="time_series",
            signal_source="expression",
            direction="long_flat",
            selection_rule="threshold",
            long_threshold=0.6,
            exit_threshold=0.4,
            max_positions=2,
            max_weight_per_position=0.5,
        )
        result = StrategyBacktester(cfg).run(self.signal_df, self.label_df)
        self.assertIn("positions", result)
        self.assertIn("trade_stats", result)
        self.assertGreaterEqual(result["metrics"]["gross_exposure"], 0.0)
