import json
import sqlite3

import manager
from core.agent_checkpoint import persist_agent_checkpoint
from core.strategy import selection_score


class _DummySummaryAgent:
    def __init__(self, *args, **kwargs):
        pass


class _ImmediateFuture:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc
        self.cancelled = False

    def result(self, timeout=None):
        if self._exc is not None:
            raise self._exc
        return self._result

    def cancel(self):
        self.cancelled = True
        return True


class _CapturingProcessPoolExecutor:
    captured_max_workers = None

    def __init__(self, max_workers=None, initializer=None, initargs=()):
        type(self).captured_max_workers = max_workers
        if initializer is not None:
            initializer(*initargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, kwargs):
        try:
            return _ImmediateFuture(result=fn(kwargs))
        except Exception as exc:
            return _ImmediateFuture(exc=exc)

    def shutdown(self, wait=True, cancel_futures=False):
        return None


class _CapturingThreadPoolExecutor:
    captured_max_workers = None

    def __init__(self, max_workers=None):
        type(self).captured_max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        try:
            return _ImmediateFuture(result=fn(*args, **kwargs))
        except Exception as exc:
            return _ImmediateFuture(exc=exc)

    def shutdown(self, wait=True, cancel_futures=False):
        return None


def test_run_swarm_caps_parallel_workers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIMINER_MAX_WORKERS_PER_SWARM", "2")
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(
        manager,
        "run_agent_task",
        lambda kwargs: {
            "role": kwargs["role_prompt"],
            "perf_metric": 0.0,
            "returns": {},
        },
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ProcessPoolExecutor",
        _CapturingProcessPoolExecutor,
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "as_completed",
        lambda futures, timeout=None: list(futures),
    )

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a", "role_b", "role_c", "role_d"],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    monkeypatch.setattr(portfolio_manager, "evaluate_and_combine", lambda results: [])
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=True)

    assert _CapturingProcessPoolExecutor.captured_max_workers == 2


def test_run_swarm_thread_executor_uses_thread_pool(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIMINER_SWARM_EXECUTOR", "thread")
    monkeypatch.setenv("AIMINER_MAX_WORKERS_PER_SWARM", "3")
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(
        manager,
        "run_agent_task",
        lambda kwargs: {
            "role": kwargs["role_prompt"],
            "perf_metric": 0.0,
            "returns": {},
        },
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ThreadPoolExecutor",
        _CapturingThreadPoolExecutor,
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ProcessPoolExecutor",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("process pool should not be used")
        ),
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "as_completed",
        lambda futures, timeout=None: list(futures),
    )
    captured = {}

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a", "role_b", "role_c", "role_d"],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    monkeypatch.setattr(
        portfolio_manager,
        "evaluate_and_combine",
        lambda results: captured.setdefault("results", list(results)),
    )
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=True)

    assert _CapturingThreadPoolExecutor.captured_max_workers == 3
    assert len(captured["results"]) == 4


def test_run_swarm_global_timeout_cancels_pending_agents(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(
        manager,
        "run_agent_task",
        lambda kwargs: {
            "role": kwargs["role_prompt"],
            "perf_metric": 0.02,
            "returns": {},
        },
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ProcessPoolExecutor",
        _CapturingProcessPoolExecutor,
    )

    def _timeout(_futures, timeout=None):
        raise manager.concurrent.futures.TimeoutError()

    monkeypatch.setattr(manager.concurrent.futures, "as_completed", _timeout)
    captured = {}

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a", "role_b"],
        data_backend="local",
        local_data_path=str(tmp_path),
        swarm_global_timeout_seconds=0.01,
    )
    monkeypatch.setattr(
        portfolio_manager,
        "evaluate_and_combine",
        lambda results: captured.setdefault("results", list(results)),
    )
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=True)

    assert captured["results"] == []


def test_run_swarm_timeout_recovers_agent_checkpoints(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(
        manager,
        "run_agent_task",
        lambda kwargs: {
            "role": kwargs["role_prompt"],
            "perf_metric": 0.02,
            "returns": {},
        },
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ProcessPoolExecutor",
        _CapturingProcessPoolExecutor,
    )

    def _timeout(_futures, timeout=None):
        raise manager.concurrent.futures.TimeoutError()

    monkeypatch.setattr(manager.concurrent.futures, "as_completed", _timeout)
    captured = {}

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a"],
        data_backend="local",
        local_data_path=str(tmp_path),
        swarm_global_timeout_seconds=0.01,
    )
    persist_agent_checkpoint(
        portfolio_manager.db_path,
        {
            "run_id": portfolio_manager.run_id,
            "agent_id": "agent_1",
            "role_prompt": "role_a",
            "iteration": 7,
            "evaluation_mode": "ricequant",
            "evaluation_engine": "pandas",
            "data_backend": "local",
            "market_profile": "cn_stock",
            "market_profiles": ["cn_stock"],
            "best_factor_snapshot": {
                "iteration": 7,
                "hypothesis": "checkpoint alpha",
                "code": "Rank($close)",
                "metrics": {"information_coefficient": 0.031},
                "returns": {"2024-01-01": 0.01, "2024-01-02": 0.02},
                "is_simulated": False,
            },
        },
        settings=portfolio_manager.settings,
    )
    monkeypatch.setattr(
        portfolio_manager,
        "evaluate_and_combine",
        lambda results: captured.setdefault("results", list(results)),
    )
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=True)

    assert len(captured["results"]) == 1
    assert captured["results"][0]["hypothesis"] == "checkpoint alpha"
    assert captured["results"][0]["perf_metric"] == 0.031


def test_run_swarm_process_pool_failure_recovers_agent_checkpoints(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    def _broken_run_agent_task(_kwargs):
        raise manager.BrokenProcessPool(
            "A process in the process pool was terminated abruptly while the "
            "future was running or pending."
        )

    monkeypatch.setattr(manager, "run_agent_task", _broken_run_agent_task)
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ProcessPoolExecutor",
        _CapturingProcessPoolExecutor,
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "as_completed",
        lambda futures, timeout=None: list(futures),
    )
    captured = {}

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a"],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    persist_agent_checkpoint(
        portfolio_manager.db_path,
        {
            "run_id": portfolio_manager.run_id,
            "agent_id": "agent_1",
            "role_prompt": "role_a",
            "iteration": 9,
            "evaluation_mode": "ricequant",
            "evaluation_engine": "pandas",
            "data_backend": "local",
            "market_profile": "cn_stock",
            "market_profiles": ["cn_stock"],
            "best_factor_snapshot": {
                "iteration": 9,
                "hypothesis": "recovered after pool break",
                "code": "Rank($close)",
                "metrics": {"information_coefficient": 0.041},
                "returns": {"2024-01-01": 0.01},
                "is_simulated": False,
            },
        },
        settings=portfolio_manager.settings,
    )
    monkeypatch.setattr(
        portfolio_manager,
        "evaluate_and_combine",
        lambda results: captured.setdefault("results", list(results)),
    )
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=True)

    assert len(captured["results"]) == 1
    assert captured["results"][0]["hypothesis"] == "recovered after pool break"
    assert captured["results"][0]["perf_metric"] == 0.041


def test_checkpoint_recovery_replaces_errored_final_result(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    persist_agent_checkpoint(
        portfolio_manager.db_path,
        {
            "run_id": portfolio_manager.run_id,
            "agent_id": "agent_2",
            "role_prompt": "波动率专家",
            "iteration": 6,
            "evaluation_mode": "ricequant",
            "evaluation_engine": "pandas",
            "data_backend": "local",
            "market_profile": "cn_stock",
            "market_profiles": ["cn_stock"],
            "best_factor_snapshot": {
                "iteration": 6,
                "hypothesis": "checkpoint alpha",
                "code": "Rank($close)",
                "metrics": {"information_coefficient": 0.0278},
                "returns": {"2024-01-01": 0.01},
                "is_simulated": False,
            },
        },
        settings=portfolio_manager.settings,
    )

    recovered = portfolio_manager._recover_checkpoint_results(
        [
            {
                "run_id": portfolio_manager.run_id,
                "agent_id": "agent_2",
                "role": "波动率专家",
                "error": "Connection error.",
            }
        ]
    )

    assert len(recovered) == 1
    assert recovered[0]["error"] is None
    assert recovered[0]["hypothesis"] == "checkpoint alpha"
    assert recovered[0]["perf_metric"] == 0.0278


def test_run_swarm_crossover_uses_dedicated_iteration_cap(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(manager, "PortfolioAgent", lambda *args, **kwargs: object())
    calls = []

    def _fake_run_agent_task(kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("agent_id") == "agent_crossover":
            return {
                "role": kwargs["role_prompt"],
                "hypothesis": "hybrid",
                "code": "Rank($close)",
                "perf_metric": 0.02,
                "metrics": {"information_coefficient": 0.02},
                "returns": {},
                "is_effective": True,
                "is_simulated": False,
            }
        return {
            "role": kwargs["role_prompt"],
            "perf_metric": 0.0,
            "returns": {},
        }

    monkeypatch.setattr(manager, "run_agent_task", _fake_run_agent_task)

    portfolio_manager = manager.PortfolioManager(
        roles=["role_a"],
        max_iterations=300,
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    portfolio_manager.summary_agent.generate_markdown_report = (
        lambda factor: "report.md"
    )

    def _seed_alpha_pool(_results):
        portfolio_manager.alpha_pool = [
            {
                "id": "alpha_a",
                "role": "role_a",
                "hypothesis": "factor a",
                "code": "Rank($close)",
                "perf_metric": 0.04,
                "metrics": {"information_coefficient": 0.04},
                "returns": {},
                "is_effective": True,
                "is_simulated": False,
            },
            {
                "id": "alpha_b",
                "role": "role_b",
                "hypothesis": "factor b",
                "code": "Rank($volume)",
                "perf_metric": 0.03,
                "metrics": {"information_coefficient": 0.03},
                "returns": {},
                "is_effective": True,
                "is_simulated": False,
            },
        ]
        return portfolio_manager.alpha_pool

    monkeypatch.setattr(portfolio_manager, "evaluate_and_combine", _seed_alpha_pool)
    monkeypatch.setattr(portfolio_manager, "evaluate_strategies", lambda: [])

    portfolio_manager.run_swarm(parallel=False)

    main_calls = [call for call in calls if call.get("agent_id") != "agent_crossover"]
    crossover_calls = [
        call for call in calls if call.get("agent_id") == "agent_crossover"
    ]
    assert main_calls[0]["max_iterations"] == 300
    assert len(crossover_calls) == 1
    assert crossover_calls[0]["max_iterations"] == 1


def test_evaluate_and_combine_accepts_serialized_returns(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    shared_returns = {
        f"2024-01-{day:02d}": float(day) / 100.0 for day in range(1, 13)
    }

    alpha_pool = portfolio_manager.evaluate_and_combine(
        [
            {
                "role": "factor one",
                "hypothesis": "serialized-one",
                "perf_metric": 0.03,
                "selection_score": 0.03,
                "market_profile": "cn_stock",
                "returns": shared_returns,
            },
            {
                "role": "factor two",
                "hypothesis": "serialized-two",
                "perf_metric": 0.04,
                "selection_score": 0.04,
                "market_profile": "cn_stock",
                "returns": shared_returns,
            },
        ]
    )

    assert len(alpha_pool) == 1
    assert alpha_pool[0]["hypothesis"] == "serialized-one"
    assert alpha_pool[0]["id"].startswith("alpha_")


def test_evaluate_and_combine_rejects_simulated_factors(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )

    alpha_pool = portfolio_manager.evaluate_and_combine(
        [
            {
                "role": "simulated factor",
                "hypothesis": "fallback metrics",
                "perf_metric": 0.12,
                "metrics": {"information_coefficient": 0.12},
                "returns": {f"2024-01-{day:02d}": 0.01 for day in range(1, 13)},
                "is_simulated": True,
            }
        ]
    )

    assert alpha_pool == []


def test_alpha_pool_json_backup_mirrors_sqlite_source_of_truth(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    with sqlite3.connect(portfolio_manager.db_path) as conn:
        conn.execute(
            """
            INSERT INTO alpha_pool (
                id, role, hypothesis, code, ic, rank_ic, metrics_json,
                returns_json, perf_metric, is_simulated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "alpha_one",
                "role",
                "hypothesis one",
                "rank(close)",
                0.02,
                0.01,
                json.dumps({"information_coefficient": 0.02}),
                json.dumps({"2024-01-01": 0.01}),
                0.02,
                0,
            ),
        )
        conn.execute(
            """
            INSERT INTO alpha_pool (
                id, role, hypothesis, code, ic, rank_ic, metrics_json,
                returns_json, perf_metric, is_simulated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "alpha_two",
                "role",
                "hypothesis two",
                "rank(open)",
                0.03,
                0.02,
                json.dumps({"information_coefficient": 0.03}),
                json.dumps({"2024-01-02": 0.02}),
                0.03,
                0,
            ),
        )
        conn.commit()

    portfolio_manager._write_alpha_pool_json_backup()
    payload = json.loads((tmp_path / "results" / "alpha_pool.json").read_text())

    assert {item["id"] for item in payload} == {"alpha_one", "alpha_two"}
    assert all("metrics" in item and "returns" in item for item in payload)


def test_evaluate_and_combine_accepts_negative_ic_by_inverting_signal(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    returns = {f"2024-01-{day:02d}": 0.01 for day in range(1, 13)}

    alpha_pool = portfolio_manager.evaluate_and_combine(
        [
            {
                "role": "negative factor",
                "hypothesis": "inverse predictive signal",
                "code": "rank(close)",
                "perf_metric": -0.03,
                "metrics": {"information_coefficient": -0.03},
                "market_profile": "cn_stock",
                "returns": returns,
            }
        ]
    )

    assert len(alpha_pool) == 1
    factor = alpha_pool[0]
    assert factor["raw_perf_metric"] == -0.03
    assert factor["perf_metric"] == 0.03
    assert factor["signal_direction"] == -1
    assert factor["code"] == "rank(close)"
    assert all(value == -0.01 for value in factor["returns"].values())


def test_evaluate_strategies_reuses_existing_agent_results(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    portfolio_manager = manager.PortfolioManager(roles=[])
    portfolio_manager.alpha_pool = [
        {
            "id": "alpha_1",
            "agent_id": "agent_1",
            "hypothesis": "existing strategy path",
            "code": "rank(open / close)",
            "perf_metric": 0.08,
            "selection_score": -99.0,
            "market_profile": "cn_stock",
            "data_backend": "local",
            "strategy_results": [
                {
                    "strategy_id": "s_low",
                    "strategy_config": {"label": "low"},
                    "metrics": {"annualized_return": 0.08, "sharpe": 0.7, "max_drawdown": -0.12},
                    "daily_returns": {"2024-01-01": 0.01},
                    "trade_stats": {},
                    "selection_score": -99.0,
                },
                {
                    "strategy_id": "s_high",
                    "strategy_config": {"label": "high"},
                    "metrics": {"annualized_return": 0.18, "sharpe": 1.4, "max_drawdown": -0.08},
                    "daily_returns": {"2024-01-01": 0.02},
                    "trade_stats": {},
                    "selection_score": -99.0,
                },
            ],
        }
    ]

    results = portfolio_manager.evaluate_strategies()

    assert len(results) == 2
    best = portfolio_manager.alpha_pool[0]["best_strategy_result"]
    assert best["raw_strategy_id"] == "s_high"
    assert portfolio_manager.alpha_pool[0]["best_strategy_id"] == best["strategy_id"]
    assert portfolio_manager.alpha_pool[0]["selection_score"] == selection_score(
        {"annualized_return": 0.18, "sharpe": 1.4, "max_drawdown": -0.08},
        factor_ic=0.08,
    )
    assert any(item["raw_strategy_id"] == "s_high" and item["is_primary"] for item in results)


def test_evaluate_strategies_consumes_agent_candidates_before_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    captured = {}

    def _fake_backtest(expression, strategy_config, **kwargs):
        captured["expression"] = expression
        captured["label"] = strategy_config.get("label")
        captured["signal_multiplier"] = kwargs.get("signal_multiplier")
        return {
            "strategy_id": "strategy_candidate",
            "run_type": "strategy_backtest",
            "status": "ok",
            "expression": expression,
            "strategy_config": strategy_config,
            "metrics": {"annualized_return": 0.12, "sharpe": 1.1, "max_drawdown": -0.09},
            "daily_returns": {"2024-01-01": 0.01},
            "positions": {},
            "trade_stats": {},
            "chart_paths": {},
            "market": strategy_config.get("market"),
            "engine": strategy_config.get("engine"),
            "label": strategy_config.get("label"),
            "ran_at": "2024-01-01T00:00:00",
        }

    import core.manual_runner as manual_runner

    monkeypatch.setattr(manual_runner, "run_manual_strategy_backtest", _fake_backtest)

    portfolio_manager = manager.PortfolioManager(roles=[])
    portfolio_manager.alpha_pool = [
        {
            "id": "alpha_2",
            "agent_id": "agent_2",
            "hypothesis": "candidate strategy path",
            "code": "rank(volume)",
            "perf_metric": 0.05,
            "signal_direction": -1,
            "market_profile": "cn_stock",
            "data_backend": "local",
            "strategy_candidates": [
                {
                    "template_name": "agent_candidate",
                    "rationale": "Agent-selected execution.",
                    "strategy_config": {
                        "label": "agent_candidate:alpha",
                        "strategy_mode": "cross_sectional",
                        "signal_source": "expression",
                        "direction": "long_short",
                        "selection_rule": "top_bottom_n",
                        "rebalance_freq": "daily",
                        "top_n": 10,
                        "bottom_n": 10,
                        "max_positions": 20,
                        "max_weight_per_position": 0.1,
                        "min_holding_days": 1,
                        "commission_bps": 5.0,
                        "slippage_bps": 5.0,
                        "market": "cn_stock",
                        "start_date": "2017-01-01",
                        "end_date": "2020-10-31",
                        "engine": "polars",
                    },
                }
            ],
        }
    ]

    results = portfolio_manager.evaluate_strategies()

    assert captured["expression"] == "rank(volume)"
    assert captured["label"] == "agent_candidate:alpha"
    assert captured["signal_multiplier"] == -1.0
    assert len(results) == 1
    assert results[0]["template_name"] == "agent_candidate"
    assert results[0]["rationale"] == "Agent-selected execution."
    best = portfolio_manager.alpha_pool[0]["best_strategy_result"]
    assert best["raw_strategy_id"] == "strategy_candidate"
    assert portfolio_manager.alpha_pool[0]["best_strategy_id"] == best["strategy_id"]
    assert portfolio_manager.alpha_pool[0]["selection_score"] == selection_score(
        {"annualized_return": 0.12, "sharpe": 1.1, "max_drawdown": -0.09},
        factor_ic=0.05,
    )


def test_evaluate_strategies_caps_parallel_workers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIMINER_MAX_STRATEGY_WORKERS", "2")
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)
    monkeypatch.setattr(
        manager.concurrent.futures,
        "ThreadPoolExecutor",
        _CapturingThreadPoolExecutor,
    )
    monkeypatch.setattr(
        manager.concurrent.futures,
        "as_completed",
        lambda futures, timeout=None: list(futures),
    )

    def _fake_backtest(expression, strategy_config, **kwargs):
        label = strategy_config.get("label")
        return {
            "strategy_id": f"strategy::{label}",
            "run_type": "strategy_backtest",
            "status": "ok",
            "expression": expression,
            "strategy_config": strategy_config,
            "metrics": {"annualized_return": 0.11, "sharpe": 1.0, "max_drawdown": -0.1},
            "daily_returns": {"2024-01-01": 0.01},
            "positions": {},
            "trade_stats": {},
            "chart_paths": {},
            "market": strategy_config.get("market"),
            "engine": strategy_config.get("engine"),
            "label": label,
            "ran_at": "2024-01-01T00:00:00",
        }

    import core.manual_runner as manual_runner

    monkeypatch.setattr(manual_runner, "run_manual_strategy_backtest", _fake_backtest)

    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    portfolio_manager.alpha_pool = [
        {
            "id": "alpha_parallel",
            "agent_id": "agent_parallel",
            "hypothesis": "parallel strategy path",
            "code": "rank(close / open)",
            "perf_metric": 0.06,
            "market_profile": "cn_stock",
            "data_backend": "local",
            "strategy_candidates": [
                {
                    "template_name": "candidate_a",
                    "strategy_config": {
                        "label": "candidate_a",
                        "market": "cn_stock",
                        "engine": "polars",
                    },
                },
                {
                    "template_name": "candidate_b",
                    "strategy_config": {
                        "label": "candidate_b",
                        "market": "cn_stock",
                        "engine": "polars",
                    },
                },
                {
                    "template_name": "candidate_c",
                    "strategy_config": {
                        "label": "candidate_c",
                        "market": "cn_stock",
                        "engine": "polars",
                    },
                },
            ],
        }
    ]

    results = portfolio_manager.evaluate_strategies()

    assert _CapturingThreadPoolExecutor.captured_max_workers == 2
    assert len(results) == 3


def test_evaluate_strategies_dedupes_correlated_strategy_returns(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(manager, "SummaryAgent", _DummySummaryAgent)

    daily_returns = {f"2024-01-{day:02d}": day / 1000.0 for day in range(1, 13)}
    portfolio_manager = manager.PortfolioManager(
        roles=[],
        data_backend="local",
        local_data_path=str(tmp_path),
    )
    portfolio_manager.alpha_pool = [
        {
            "id": "alpha_keep",
            "agent_id": "agent_1",
            "role": "higher score",
            "hypothesis": "keep",
            "code": "rank(close)",
            "perf_metric": 0.08,
            "market_profile": "cn_stock",
            "data_backend": "local",
            "strategy_results": [
                {
                    "strategy_id": "raw_keep",
                    "strategy_config": {"label": "keep"},
                    "metrics": {"annualized_return": 0.20, "sharpe": 1.5, "max_drawdown": -0.05},
                    "daily_returns": daily_returns,
                    "trade_stats": {},
                }
            ],
        },
        {
            "id": "alpha_drop",
            "agent_id": "agent_2",
            "role": "lower score",
            "hypothesis": "drop",
            "code": "rank(open)",
            "perf_metric": 0.07,
            "market_profile": "cn_stock",
            "data_backend": "local",
            "strategy_results": [
                {
                    "strategy_id": "raw_drop",
                    "strategy_config": {"label": "drop"},
                    "metrics": {"annualized_return": 0.10, "sharpe": 0.8, "max_drawdown": -0.08},
                    "daily_returns": daily_returns,
                    "trade_stats": {},
                }
            ],
        },
    ]

    results = portfolio_manager.evaluate_strategies()

    assert [factor["id"] for factor in portfolio_manager.alpha_pool] == ["alpha_keep"]
    assert len(results) == 1
    assert results[0]["source_factor_id"] == "alpha_keep"
