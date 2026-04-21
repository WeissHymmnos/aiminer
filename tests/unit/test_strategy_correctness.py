import sqlite3

import pandas as pd

from core import manual_runner
from core.strategy import _normalize_positions, _rebalance_mask, persist_strategy_result


class _FakeStrategyEvaluator:
    def __init__(self, expression: str):
        self.expression = expression

    def fetch_data(self):
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        index = pd.MultiIndex.from_product(
            [dates, ["A"]], names=["datetime", "instrument"]
        )
        self.factor_data = pd.DataFrame(
            {self.expression: [0.2, 0.8, 0.3, 0.9, 0.4]},
            index=index,
        )
        self.label_data = pd.DataFrame(
            {"label": [0.01, 0.02, -0.01, 0.03, 0.00]},
            index=index,
        )

    def compute_factors(self):
        return None


def test_normalize_positions_does_not_reinflate_clipped_single_name():
    row = pd.Series({"A": 1.0, "B": 0.0})

    normalized = _normalize_positions(row, max_weight=0.10)

    assert normalized["A"] == 0.10
    assert normalized.abs().sum() == 0.10


def test_normalize_positions_respects_cap_after_gross_scaling():
    row = pd.Series({"A": 1.0, "B": 1.0, "C": -1.0})

    normalized = _normalize_positions(row, max_weight=0.20)

    assert float(normalized.abs().max()) <= 0.20
    assert round(float(normalized.abs().sum()), 10) == 0.60


def test_rebalance_mask_marks_first_day_of_week_and_month_only():
    index = pd.to_datetime(
        [
            "2024-01-29",
            "2024-01-30",
            "2024-02-01",
            "2024-02-02",
            "2024-02-05",
        ]
    )

    weekly = _rebalance_mask(index, "weekly").tolist()
    monthly = _rebalance_mask(index, "monthly").tolist()

    assert weekly == [True, False, False, False, True]
    assert monthly == [True, False, True, False, False]


def test_strategy_persistence_keeps_run_scoped_rows_for_same_cache_key(tmp_path):
    db_path = tmp_path / "alpha_miner.db"
    base_payload = {
        "run_type": "strategy_backtest",
        "strategy_config": {"strategy_mode": "cross_sectional", "signal_source": "expression"},
        "expression": "rank(close)",
        "metrics": {"sharpe": 1.0},
        "daily_returns": {"2024-01-01": 0.01},
        "positions": {},
        "trade_stats": {},
        "chart_paths": {},
        "market": "cn_stock",
        "engine": "pandas",
        "ran_at": "2024-01-01T00:00:00",
        "cache_key": "strategy_cache_same",
    }

    persist_strategy_result(
        db_path,
        {
            **base_payload,
            "strategy_id": "strategy_run_a",
            "run_id": "run_a",
            "source_factor_id": "alpha_1",
            "candidate_rank": 1,
        },
    )
    persist_strategy_result(
        db_path,
        {
            **base_payload,
            "strategy_id": "strategy_run_b",
            "run_id": "run_b",
            "source_factor_id": "alpha_1",
            "candidate_rank": 1,
        },
    )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT strategy_id, run_id, cache_key FROM strategy_backtests ORDER BY run_id"
        ).fetchall()

    assert rows == [
        ("strategy_run_a", "run_a", "strategy_cache_same"),
        ("strategy_run_b", "run_b", "strategy_cache_same"),
    ]


def test_manual_strategy_cache_materializes_run_scoped_strategy_ids(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        manual_runner,
        "validate_expression",
        lambda _expression: (True, "ok"),
    )
    build_calls = []

    def _build_evaluator(factor_expressions, **_kwargs):
        build_calls.append(factor_expressions[0])
        return _FakeStrategyEvaluator(factor_expressions[0])

    monkeypatch.setattr("core.evaluator_factory.build_evaluator", _build_evaluator)
    config = {
        "label": "cache-test",
        "strategy_mode": "time_series",
        "direction": "long_flat",
        "selection_rule": "threshold",
        "long_threshold": 0.5,
        "exit_threshold": 0.4,
        "start_date": "2024-01-01",
        "end_date": "2024-01-05",
        "engine": "pandas",
    }

    first = manual_runner.run_manual_strategy_backtest(
        "rank(close)",
        config,
        data_backend="local",
        market_profile="cn_stock",
        local_data_path=str(tmp_path),
        run_id="run_a",
        source_factor_id="alpha_1",
        candidate_rank=1,
    )
    second = manual_runner.run_manual_strategy_backtest(
        "rank(close)",
        config,
        data_backend="local",
        market_profile="cn_stock",
        local_data_path=str(tmp_path),
        run_id="run_b",
        source_factor_id="alpha_1",
        candidate_rank=1,
    )

    assert build_calls == ["rank(close)"]
    assert first["cache_key"] == second["cache_key"]
    assert first["strategy_id"] != second["strategy_id"]
    assert second["cache_hit"] is True

    with sqlite3.connect(tmp_path / "results" / "alpha_miner.db") as conn:
        rows = conn.execute(
            "SELECT strategy_id, run_id, cache_key FROM strategy_backtests ORDER BY run_id"
        ).fetchall()

    assert rows == [
        (first["strategy_id"], "run_a", first["cache_key"]),
        (second["strategy_id"], "run_b", second["cache_key"]),
    ]


def test_strategy_cache_key_includes_signal_multiplier():
    config = {
        "strategy_mode": "time_series",
        "direction": "long_flat",
        "selection_rule": "threshold",
        "long_threshold": 0.5,
    }

    normal = manual_runner.strategy_cache_key_for("rank(close)", config)
    inverted = manual_runner.strategy_cache_key_for(
        "rank(close)",
        config,
        signal_multiplier=-1.0,
    )

    assert normal != inverted
