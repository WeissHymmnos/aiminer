"""Unit tests for factor PnL turnover tracking and transaction costs."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from aiminer.agents.eval_agent import EvalAgent
from aiminer.core.alphaeval.holdout import segment_stats
from aiminer.core.alphaeval.local_eval import LocalDataEval
from aiminer.core.alphaeval.rq_eval import RiceQuantEval
from aiminer.core.evaluator_factory import (
    EvaluationConfig,
    build_evaluator,
    evaluation_config_from_mapping,
)


def _make_two_day_synthetic_data() -> pd.DataFrame:
    """Create a synthetic 2-day dataset for testing turnover accuracy."""
    idx = pd.MultiIndex.from_tuples(
        [
            (pd.Timestamp("2020-01-01"), "stock_A"),
            (pd.Timestamp("2020-01-01"), "stock_B"),
            (pd.Timestamp("2020-01-02"), "stock_A"),
            (pd.Timestamp("2020-01-02"), "stock_B"),
        ],
        names=["datetime", "instrument"],
    )
    # Day 1: A=+1.0, B=-1.0 -> weights: A=+0.5, B=-0.5
    # Day 2: A=-1.0, B=+1.0 -> weights: A=-0.5, B=+0.5
    return pd.DataFrame(
        {
            "factor": [1.0, -1.0, -1.0, 1.0],
            "label": [0.02, -0.01, -0.01, 0.02],
        },
        index=idx,
    )


def _make_multi_day_synthetic_data(n_days: int = 10) -> pd.DataFrame:
    """Create synthetic multi-day panel data with positive returns."""
    dates = pd.date_range("2020-01-01", periods=n_days, freq="B")
    records = []
    for i, dt in enumerate(dates):
        sign = 1.0 if (i % 2 == 0) else -1.0
        records.append((dt, "stock_A", sign * 1.5, 0.01 * sign))
        records.append((dt, "stock_B", -sign * 1.5, -0.01 * sign))
        records.append((dt, "stock_C", 0.5, 0.005))
    idx = pd.MultiIndex.from_tuples(
        [(r[0], r[1]) for r in records], names=["datetime", "instrument"]
    )
    return pd.DataFrame(
        {"factor": [r[2] for r in records], "label": [r[3] for r in records]},
        index=idx,
    )


def test_turnover_accuracy_synthetic_2day_weights():
    """Verify daily turnover computation on synthetic 2-day weights."""
    evaluator = RiceQuantEval(
        factor_expressions=["close / open"],
        cost_bps=5.0,
        skip_auth=True,
    )
    all_data = _make_two_day_synthetic_data()

    net_ret = evaluator.calculate_pnl(all_data)

    # Weights:
    # Day 1: stock_A=0.5, stock_B=-0.5 (sum abs = 1.0)
    # Day 2: stock_A=-0.5, stock_B=0.5 (sum abs = 1.0)
    # Day 1 turnover is 0.0 (no prior day in window)
    # Day 2 turnover is (| -0.5 - 0.5 | + | 0.5 - (-0.5) |) / 2 = 2.0 / 2 = 1.0
    assert len(evaluator.turnover_series) == 2
    assert evaluator.turnover_series.iloc[0] == pytest.approx(0.0)
    assert evaluator.turnover_series.iloc[1] == pytest.approx(1.0)
    assert evaluator.mean_turnover == pytest.approx(0.5)
    assert evaluator.turnover == pytest.approx(0.5)

    # Day 2 cost drag: 1.0 * (5.0 / 10000) = 0.0005
    # Gross day 2: -0.5 * (-0.01) + 0.5 * 0.02 = 0.005 + 0.01 = 0.015
    # Net day 2: 0.015 - 0.0005 = 0.0145
    assert evaluator.gross_daily_returns_series.iloc[1] == pytest.approx(0.015)
    assert net_ret.iloc[1] == pytest.approx(0.0145)


def test_turnover_accuracy_partial_rebalance():
    """Test partial turnover where one stock is kept, one replaced."""
    idx = pd.MultiIndex.from_tuples(
        [
            (pd.Timestamp("2020-01-01"), "stock_A"),
            (pd.Timestamp("2020-01-01"), "stock_B"),
            (pd.Timestamp("2020-01-02"), "stock_A"),
            (pd.Timestamp("2020-01-02"), "stock_C"),
        ],
        names=["datetime", "instrument"],
    )
    # Day 1: A=1.0, B=-1.0 -> weights: A=0.5, B=-0.5, C=0.0
    # Day 2: A=1.0, C=-1.0 -> weights: A=0.5, B=0.0, C=-0.5
    # Diff on day 2: A: |0.5 - 0.5|=0; B: |0 - (-0.5)|=0.5; C: |-0.5 - 0|=0.5
    # Turnover day 2: (0 + 0.5 + 0.5) / 2 = 0.5
    df = pd.DataFrame(
        {
            "factor": [1.0, -1.0, 1.0, -1.0],
            "label": [0.01, 0.02, 0.01, 0.02],
        },
        index=idx,
    )
    evaluator = RiceQuantEval(
        factor_expressions=["close"], cost_bps=0.0, skip_auth=True
    )
    evaluator.calculate_pnl(df)
    assert evaluator.turnover_series.iloc[0] == pytest.approx(0.0)
    assert evaluator.turnover_series.iloc[1] == pytest.approx(0.5)


def test_cost_bps_zero_yields_net_equal_gross():
    """Test that cost_bps = 0 yields identical net and gross metrics."""
    evaluator = RiceQuantEval(
        factor_expressions=["close"],
        cost_bps=0.0,
        skip_auth=True,
    )
    all_data = _make_multi_day_synthetic_data(n_days=15)
    net_ret = evaluator.calculate_pnl(all_data)

    assert np.allclose(
        evaluator.daily_returns_series.values,
        evaluator.gross_daily_returns_series.values,
    )
    assert np.allclose(net_ret.values, evaluator.gross_daily_returns_series.values)
    assert evaluator.sharpe == pytest.approx(evaluator.gross_sharpe)
    assert evaluator.max_dd == pytest.approx(evaluator.gross_max_dd)


def test_positive_cost_bps_reduces_net_sharpe_with_turnover():
    """Test that positive cost_bps monotonically reduces net Sharpe."""
    all_data = _make_multi_day_synthetic_data(n_days=20)

    eval_0 = RiceQuantEval(
        factor_expressions=["close"], cost_bps=0.0, skip_auth=True
    )
    eval_0.calculate_pnl(all_data)

    eval_5 = RiceQuantEval(
        factor_expressions=["close"], cost_bps=5.0, skip_auth=True
    )
    eval_5.calculate_pnl(all_data)

    eval_20 = RiceQuantEval(
        factor_expressions=["close"], cost_bps=20.0, skip_auth=True
    )
    eval_20.calculate_pnl(all_data)

    assert eval_0.mean_turnover > 0.0
    assert eval_0.sharpe == pytest.approx(eval_0.gross_sharpe)
    assert eval_5.sharpe < eval_0.sharpe
    assert eval_20.sharpe < eval_5.sharpe
    assert eval_5.gross_sharpe == pytest.approx(eval_0.gross_sharpe)
    assert eval_20.gross_sharpe == pytest.approx(eval_0.gross_sharpe)


def test_higher_turnover_suffers_greater_cost_drag():
    """Factors with higher turnover should suffer greater Sharpe reduction."""
    dates = pd.date_range("2020-01-01", periods=10, freq="B")

    # Static factor: identical weights every day (turnover = 0)
    static_records = []
    for dt in dates:
        static_records.append((dt, "stock_A", 1.0, 0.01))
        static_records.append((dt, "stock_B", -1.0, -0.01))
    static_df = pd.DataFrame(
        {
            "factor": [r[2] for r in static_records],
            "label": [r[3] for r in static_records],
        },
        index=pd.MultiIndex.from_tuples(
            [(r[0], r[1]) for r in static_records],
            names=["datetime", "instrument"],
        ),
    )

    # Flipping factor: signs flip every day (turnover = 1.0 on days 1+)
    flip_records = []
    for i, dt in enumerate(dates):
        s = 1.0 if (i % 2 == 0) else -1.0
        # Label adjusts so gross returns remain identical to static (+0.01)
        flip_records.append((dt, "stock_A", s, 0.01 * s))
        flip_records.append((dt, "stock_B", -s, -0.01 * s))
    flip_df = pd.DataFrame(
        {
            "factor": [r[2] for r in flip_records],
            "label": [r[3] for r in flip_records],
        },
        index=pd.MultiIndex.from_tuples(
            [(r[0], r[1]) for r in flip_records],
            names=["datetime", "instrument"],
        ),
    )

    static_eval = RiceQuantEval(
        factor_expressions=["close"], cost_bps=10.0, skip_auth=True
    )
    static_eval.calculate_pnl(static_df)

    flip_eval = RiceQuantEval(
        factor_expressions=["close"], cost_bps=10.0, skip_auth=True
    )
    flip_eval.calculate_pnl(flip_df)

    # Static factor has 0 turnover, so net Sharpe equals gross Sharpe
    assert static_eval.mean_turnover == pytest.approx(0.0)
    assert static_eval.sharpe == pytest.approx(static_eval.gross_sharpe)

    # Flipping factor has ~0.9 turnover, net Sharpe is dragged down
    assert flip_eval.mean_turnover > 0.8
    assert flip_eval.sharpe < flip_eval.gross_sharpe
    assert flip_eval.sharpe < static_eval.sharpe


def test_local_data_eval_cost_bps_propagation():
    """Verify LocalDataEval accepts and passes cost_bps."""
    evaluator = LocalDataEval(
        factor_expressions=["close"],
        local_data_path="dummy_path",
        cost_bps=7.5,
    )
    assert evaluator.cost_bps == 7.5


def test_evaluator_factory_cost_bps():
    """Verify EvaluationConfig and build_evaluator propagate cost_bps."""
    # 1. Explicit in mapping
    cfg1 = evaluation_config_from_mapping(
        {"data_backend": "ricequant", "cost_bps": 8.0}
    )
    assert cfg1.cost_bps == 8.0

    # 2. Env variable fallback
    old_env = os.environ.get("AIMINER_COST_BPS")
    try:
        os.environ["AIMINER_COST_BPS"] = "12.0"
        cfg2 = evaluation_config_from_mapping({"data_backend": "ricequant"})
        assert cfg2.cost_bps == 12.0
    finally:
        if old_env is not None:
            os.environ["AIMINER_COST_BPS"] = old_env
        else:
            os.environ.pop("AIMINER_COST_BPS", None)

    # 3. Default fallback (5.0)
    cfg3 = evaluation_config_from_mapping({"data_backend": "ricequant"})
    assert cfg3.cost_bps == 5.0

    # 4. build_evaluator passes cost_bps to RiceQuantEval
    ev = build_evaluator(
        factor_expressions=["close"],
        config=EvaluationConfig(
            data_backend="ricequant",
            evaluation_engine="pandas",
            market_mode="single",
            market_profile="cn_stock",
            market_profiles=["cn_stock"],
            cost_bps=6.5,
        ),
    )
    assert getattr(ev, "cost_bps", None) == 6.5


def test_eval_agent_collects_turnover_and_gross_sharpe():
    """Verify EvalAgent._collect_evaluator_metrics exposes new metrics."""
    mock_eval = MagicMock()
    mock_eval.ic = 0.08
    mock_eval.rankic = 0.07
    mock_eval.sharpe = 1.8
    mock_eval.gross_sharpe = 2.4
    mock_eval.turnover = 0.45
    mock_eval.mean_turnover = 0.45
    mock_eval.max_dd = -0.08
    mock_eval.is_ic = 0.05
    mock_eval.is_rankic = 0.04
    mock_eval.is_sharpe = 1.4
    mock_eval.is_gross_sharpe = 1.9
    mock_eval.is_turnover = 0.40
    mock_eval.is_max_dd = -0.05
    mock_eval.val_ic = 0.06
    mock_eval.val_rankic = 0.05
    mock_eval.val_sharpe = 1.5
    mock_eval.val_gross_sharpe = 2.0
    mock_eval.val_turnover = 0.42
    mock_eval.oos_ic = 0.03
    mock_eval.oos_rankic = 0.02
    mock_eval.oos_sharpe = 1.1
    mock_eval.oos_gross_sharpe = 1.6
    mock_eval.oos_turnover = 0.48
    mock_eval.oos_max_dd = -0.09
    mock_eval.valid_split_date = "2021-01-01"
    mock_eval.oos_split_date = "2023-01-01"
    mock_eval.rre = 0.85
    mock_eval.plot_paths = {}
    mock_eval.daily_returns = {}

    metrics = EvalAgent._collect_evaluator_metrics(mock_eval)

    # Train segment agent-facing metrics
    assert metrics["turnover"] == pytest.approx(0.40)
    assert metrics["gross_sharpe"] == pytest.approx(1.9)
    assert metrics["sharpe"] == pytest.approx(1.4)
    assert metrics["metric_window"] == "train"

    # Holdout payload
    holdout = metrics["_holdout"]
    assert holdout["full_gross_sharpe"] == pytest.approx(2.4)
    assert holdout["full_turnover"] == pytest.approx(0.45)
    assert holdout["val_gross_sharpe"] == pytest.approx(2.0)
    assert holdout["val_turnover"] == pytest.approx(0.42)
    assert holdout["oos_gross_sharpe"] == pytest.approx(1.6)
    assert holdout["oos_turnover"] == pytest.approx(0.48)


def test_segment_stats_with_turnover_and_gross():
    """Verify segment_stats computes turnover and gross Sharpe correctly."""
    dates = pd.date_range("2020-01-01", periods=10, freq="D")
    ic = pd.Series([0.05] * 10, index=dates)
    rank_ic = pd.Series([0.04] * 10, index=dates)
    net_ret = pd.Series([0.008, -0.004] * 5, index=dates)
    gross_ret = pd.Series([0.010, -0.002] * 5, index=dates)
    turnover = pd.Series([0.2] * 10, index=dates)

    stats = segment_stats(
        ic,
        rank_ic,
        net_ret,
        "2020-01-01",
        "2020-01-06",
        turnover_series=turnover,
        gross_daily_returns=gross_ret,
    )
    assert stats is not None
    assert stats["turnover"] == pytest.approx(0.2)
    assert stats["gross_sharpe"] is not None
    assert stats["gross_sharpe"] > stats["sharpe"]
    assert stats["gross_max_dd"] is not None


def test_empty_all_data_safely_handled():
    """Verify calculate_pnl handles empty DataFrame gracefully."""
    evaluator = RiceQuantEval(
        factor_expressions=["close"], cost_bps=5.0, skip_auth=True
    )
    empty_df = pd.DataFrame(columns=["factor", "label"])
    ret = evaluator.calculate_pnl(empty_df)
    assert ret.empty
    assert evaluator.mean_turnover == 0.0
    assert evaluator.turnover == 0.0
    assert evaluator.sharpe == 0.0
    assert evaluator.gross_sharpe == 0.0
    assert evaluator.max_dd == 0.0
    assert evaluator.gross_max_dd == 0.0


def test_generate_plots_with_net_gross_turnover(tmp_path):
    """Verify generate_plots outputs equity with turnover and standalone."""
    evaluator = RiceQuantEval(
        factor_expressions=["close"],
        cost_bps=5.0,
        output_dir=str(tmp_path),
        skip_auth=True,
    )
    all_data = _make_multi_day_synthetic_data(n_days=10)
    net_ret = evaluator.calculate_pnl(all_data)
    layer_ret = pd.DataFrame(
        {"G1": [0.01] * len(net_ret), "G2": [-0.01] * len(net_ret)},
        index=net_ret.index,
    )

    plot_paths = evaluator.generate_plots(
        net_ret, layer_ret, "alpha_test_factor"
    )
    assert "equity" in plot_paths
    assert os.path.exists(plot_paths["equity"])
    assert "turnover" in plot_paths
    assert os.path.exists(plot_paths["turnover"])
    assert "layers" in plot_paths
    assert os.path.exists(plot_paths["layers"])
