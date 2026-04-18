import unittest

import numpy as np
import pandas as pd

from core.strategy import (
    StrategyBacktester,
    StrategyConfig,
    _split_walk_forward_windows,
    aggregate_walk_forward,
    selection_score,
)


def _make_panel(n_days: int = 252, n_assets: int = 8, seed: int = 0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-02", periods=n_days, freq="B")
    cols = [f"S{i}" for i in range(n_assets)]
    signal = pd.DataFrame(rng.standard_normal((n_days, n_assets)), index=dates, columns=cols)
    label = pd.DataFrame(
        rng.standard_normal((n_days, n_assets)) * 0.01, index=dates, columns=cols
    )
    return signal, label


class TestSplitWindows(unittest.TestCase):
    def test_returns_empty_for_short_index(self):
        idx = pd.date_range("2020-01-01", periods=20, freq="B")
        self.assertEqual(_split_walk_forward_windows(idx, n_windows=4, min_window_days=63), [])

    def test_returns_n_non_overlapping_windows(self):
        idx = pd.date_range("2020-01-01", periods=252, freq="B")
        windows = _split_walk_forward_windows(idx, n_windows=4, min_window_days=63)
        self.assertEqual(len(windows), 4)
        # Check non-overlap & monotone
        for (s1, e1), (s2, _) in zip(windows, windows[1:]):
            self.assertLess(e1, s2)

    def test_clamps_when_index_short(self):
        idx = pd.date_range("2020-01-01", periods=130, freq="B")
        windows = _split_walk_forward_windows(idx, n_windows=4, min_window_days=63)
        # Can only fit 2 windows of 63 days into 130.
        self.assertEqual(len(windows), 2)


class TestAggregateWalkForward(unittest.TestCase):
    def test_empty_returns_zeros(self):
        agg = aggregate_walk_forward([])
        self.assertEqual(agg["n_windows"], 0)
        self.assertEqual(agg["mean_sharpe"], 0.0)

    def test_consistency_counts_positive_windows(self):
        per_window = [
            {"sharpe": 1.0, "annualized_return": 0.1},
            {"sharpe": -0.5, "annualized_return": -0.05},
            {"sharpe": 0.8, "annualized_return": 0.08},
            {"sharpe": 0.4, "annualized_return": 0.05},
        ]
        agg = aggregate_walk_forward(per_window)
        self.assertEqual(agg["n_windows"], 4)
        self.assertAlmostEqual(agg["consistency"], 0.75)
        self.assertAlmostEqual(agg["min_sharpe"], -0.5)
        self.assertAlmostEqual(agg["mean_sharpe"], (1.0 - 0.5 + 0.8 + 0.4) / 4)


class TestRunWalkForward(unittest.TestCase):
    def test_attaches_walk_forward_block(self):
        signal, label = _make_panel(n_days=252, n_assets=8, seed=1)
        cfg = StrategyConfig(
            label="cs_top_bottom_test",
            strategy_mode="cross_sectional",
            direction="long_short",
            selection_rule="top_bottom_n",
            top_n=2,
            bottom_n=2,
            max_positions=4,
            max_weight_per_position=0.25,
            min_holding_days=1,
        )
        result = StrategyBacktester(cfg).run_walk_forward(signal, label, n_windows=4, min_window_days=40)

        self.assertIn("walk_forward", result)
        wf = result["walk_forward"]
        self.assertGreater(len(wf["windows"]), 0)
        self.assertIn("aggregate", wf)
        self.assertEqual(wf["aggregate"]["n_windows"], len(wf["windows"]))
        # Each window carries a date range and core metrics
        for window in wf["windows"]:
            self.assertIn("start", window)
            self.assertIn("end", window)
            self.assertIn("sharpe", window)
            self.assertIn("annualized_return", window)

    def test_falls_back_when_too_short(self):
        signal, label = _make_panel(n_days=20, n_assets=4, seed=2)
        cfg = StrategyConfig(
            label="cs_short_test",
            strategy_mode="cross_sectional",
            direction="long_only",
            selection_rule="top_n",
            top_n=2,
            max_positions=2,
            max_weight_per_position=0.5,
        )
        result = StrategyBacktester(cfg).run_walk_forward(signal, label, n_windows=4, min_window_days=63)

        self.assertIn("walk_forward", result)
        self.assertEqual(result["walk_forward"]["aggregate"]["n_windows"], 0)
        # Full-sample run still populated.
        self.assertIn("metrics", result)


class TestSelectionScoreWithWalkForward(unittest.TestCase):
    def setUp(self):
        self.metrics = {
            "annualized_return": 0.10,
            "sharpe": 1.0,
            "max_drawdown": -0.10,
            "turnover": 0.5,
            "cost_drag": 0.01,
        }

    def test_no_walk_forward_uses_in_sample_only(self):
        score_a = selection_score(self.metrics, factor_ic=0.05)
        score_b = selection_score(self.metrics, factor_ic=0.05, walk_forward={"n_windows": 0})
        self.assertEqual(score_a, score_b)

    def test_robust_oos_outperforms_lucky_window(self):
        wf_robust = {
            "n_windows": 4, "mean_sharpe": 0.9, "min_sharpe": 0.6,
            "consistency": 1.0, "sharpe_std": 0.2,
        }
        wf_lucky = {
            "n_windows": 4, "mean_sharpe": 0.9, "min_sharpe": -1.0,
            "consistency": 0.5, "sharpe_std": 1.5,
        }
        score_robust = selection_score(self.metrics, factor_ic=0.05, walk_forward=wf_robust)
        score_lucky = selection_score(self.metrics, factor_ic=0.05, walk_forward=wf_lucky)
        self.assertGreater(score_robust, score_lucky)

    def test_single_window_is_ignored(self):
        wf_one = {"n_windows": 1, "min_sharpe": -2.0, "consistency": 0.0, "sharpe_std": 0.0}
        score_with = selection_score(self.metrics, walk_forward=wf_one)
        score_without = selection_score(self.metrics)
        self.assertEqual(score_with, score_without)


if __name__ == "__main__":
    unittest.main()
