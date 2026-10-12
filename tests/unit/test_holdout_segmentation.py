"""Unit tests for train / validation / test holdout segmentation and anti-leakage."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from aiminer.agents.eval_agent import EvalAgent
from aiminer.core.alphaeval.holdout import (
    DEFAULT_OOS_SPLIT_DATE,
    DEFAULT_VALID_SPLIT_DATE,
    resolve_split_dates,
    segment_stats,
)
from aiminer.core.alphaeval.rq_eval import RiceQuantEval


def test_resolve_split_dates_defaults():
    valid, oos = resolve_split_dates("2018-01-01", "2025-12-31")
    assert valid == DEFAULT_VALID_SPLIT_DATE
    assert oos == DEFAULT_OOS_SPLIT_DATE


def test_resolve_split_dates_custom():
    valid, oos = resolve_split_dates(
        "2018-01-01", "2025-12-31", "2020-01-01", "2022-01-01"
    )
    assert valid == "2020-01-01"
    assert oos == "2022-01-01"


def test_resolve_split_dates_invalid_order():
    with pytest.raises(ValueError, match="must not be after"):
        resolve_split_dates(
            "2018-01-01", "2025-12-31", "2023-01-01", "2021-01-01"
        )


def test_resolve_split_dates_auto_split_when_out_of_range():
    # If the window is 2015-01-01 to 2017-01-01, default dates (2021, 2023) are out of range
    valid, oos = resolve_split_dates("2015-01-01", "2017-01-01")
    assert "2015" <= valid <= "2017"
    assert valid < oos <= "2017"


def test_segment_stats_no_fallback_on_empty():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    ic = pd.Series(0.05, index=dates)
    rank_ic = pd.Series(0.04, index=dates)
    ret = pd.Series(0.001, index=dates)

    # Slice strictly outside dates
    stats = segment_stats(ic, rank_ic, ret, "2021-01-01", "2022-01-01")
    assert stats is None


def test_segment_stats_computation():
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    ic = pd.Series([0.05] * 10, index=dates)
    rank_ic = pd.Series([0.04] * 10, index=dates)
    ret = pd.Series([0.01, -0.005] * 5, index=dates)

    stats = segment_stats(ic, rank_ic, ret, "2020-01-01", "2020-01-06")
    assert stats is not None
    assert stats["ic"] == 0.05
    assert stats["rank_ic"] == 0.04
    assert stats["n_days"] == 5
    assert stats["sharpe"] is not None


def test_eval_agent_holdout_isolation():
    """Verify that agent-facing metrics contain only train IC, and holdout is kept separate."""
    evaluator = MagicMock()
    evaluator.ic = 0.0888  # full window IC
    evaluator.rankic = 0.0777
    evaluator.sharpe = 2.0
    evaluator.max_dd = -0.05
    evaluator.is_ic = 0.0555  # train segment IC
    evaluator.is_rankic = 0.0444
    evaluator.is_sharpe = 1.5
    evaluator.is_max_dd = -0.03
    evaluator.val_ic = 0.0666  # validation IC
    evaluator.val_rankic = 0.0555
    evaluator.oos_ic = 0.0333  # OOS IC
    evaluator.oos_rankic = 0.0222
    evaluator.valid_split_date = "2021-01-01"
    evaluator.oos_split_date = "2023-01-01"
    evaluator.rre = 0.8
    evaluator.plot_paths = {}
    evaluator.daily_returns = {}

    metrics = EvalAgent._collect_evaluator_metrics(evaluator)

    # Agent-facing metrics must reflect train segment only
    assert metrics["information_coefficient"] == 0.0555
    assert metrics["rank_ic"] == 0.0444
    assert metrics["metric_window"] == "train"

    # Holdout must be segregated under _holdout
    holdout = metrics["_holdout"]
    assert holdout["full_ic"] == 0.0888
    assert holdout["val_ic"] == 0.0666
    assert holdout["oos_ic"] == 0.0333
