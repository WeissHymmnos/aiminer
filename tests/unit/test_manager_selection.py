import unittest
import tempfile
from unittest.mock import patch

import pandas as pd

from manager import PortfolioManager


class TestPortfolioManagerSelection(unittest.TestCase):
    @patch("manager.SummaryAgent")
    def test_evaluate_and_combine_filters_threshold_and_correlation(self, mock_summary):
        mock_summary.return_value = object()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(
                roles=["role-a", "role-b", "role-c"],
                llm_provider="ollama",
                results_dir=tmpdir,
            )

            dates = pd.date_range("2024-01-01", periods=12)
            strong = pd.Series(range(12), index=dates, dtype=float)
            correlated = strong * 2
            weak = pd.Series([0.0] * 12, index=dates, dtype=float)

            results = [
                {
                    "role": "role-a",
                    "perf_metric": 0.02,
                    "returns": strong,
                    "metrics": {"information_coefficient": 0.02},
                },
                {
                    "role": "role-b",
                    "perf_metric": 0.03,
                    "returns": correlated,
                    "metrics": {"information_coefficient": 0.03},
                },
                {
                    "role": "role-c",
                    "perf_metric": 0.001,
                    "returns": weak,
                    "metrics": {"information_coefficient": 0.001},
                },
            ]

            pool = manager.evaluate_and_combine(results)
            self.assertEqual(len(pool), 1)
            self.assertEqual(pool[0]["role"], "role-a")

    @patch("manager.SummaryAgent")
    def test_dispatch_tasks_assigns_run_and_agent_ids(self, mock_summary):
        mock_summary.return_value = object()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PortfolioManager(
                roles=["role-a", "role-b"],
                llm_provider="ollama",
                results_dir=tmpdir,
            )
            manager.dispatch_tasks()

            self.assertEqual(len(manager.researchers), 2)
            self.assertEqual(manager.researchers[0]["run_id"], manager.run_id)
            self.assertEqual(manager.researchers[0]["agent_id"], "agent_01")
            self.assertEqual(manager.researchers[1]["agent_id"], "agent_02")
