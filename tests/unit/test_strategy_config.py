import unittest

from core.strategy import StrategyConfig


class TestStrategyConfig(unittest.TestCase):
    def test_cross_sectional_top_bottom_valid(self):
        cfg = StrategyConfig(
            strategy_mode="cross_sectional",
            signal_source="expression",
            direction="long_short",
            selection_rule="top_bottom_n",
            top_n=10,
            bottom_n=10,
        )
        self.assertEqual(cfg.top_n, 10)
        self.assertEqual(cfg.bottom_n, 10)

    def test_time_series_requires_threshold_rule(self):
        with self.assertRaises(ValueError):
            StrategyConfig(
                strategy_mode="time_series",
                signal_source="expression",
                direction="long_short",
                selection_rule="top_n",
                top_n=5,
            )

    def test_threshold_rule_requires_thresholds(self):
        with self.assertRaises(ValueError):
            StrategyConfig(
                strategy_mode="cross_sectional",
                signal_source="expression",
                direction="long_only",
                selection_rule="threshold",
            )
