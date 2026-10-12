"""Unit tests for modular manager components and structured exceptions."""

from __future__ import annotations

import pandas as pd
import pytest

from aiminer.core.exceptions import (
    AIMinerError,
    ConcurrencyError,
    DataContractError,
    EvaluationError,
    LLMCallError,
    LLMError,
    QuantError,
    WorkflowError,
)
from aiminer.crossover import (
    accept_crossover_result,
    build_crossover_role,
    select_crossover_parents,
)
from aiminer.persistence import _serialize_returns, init_portfolio_db
from aiminer.scheduler import (
    _bounded_worker_count,
    _configured_positive_int,
    _configured_swarm_executor,
    _configured_timeout,
    _configured_worker_limit,
    _is_broken_process_pool_error,
)
from aiminer.selector import (
    _coerce_returns_series,
    _invert_returns,
    _orient_negative_ic_factor,
    _series_correlation,
    cull_alpha_pool,
    dedupe_alpha_pool_by_returns,
    factor_score,
)


def test_exception_hierarchy():
    err = EvaluationError("eval failed")
    assert isinstance(err, QuantError)
    assert isinstance(err, AIMinerError)

    dc_err = DataContractError("schema violation")
    assert isinstance(dc_err, QuantError)
    assert isinstance(dc_err, ValueError)

    llm_err = LLMCallError("timeout")
    assert isinstance(llm_err, LLMError)
    assert isinstance(llm_err, AIMinerError)

    wf_err = ConcurrencyError("pool failed")
    assert isinstance(wf_err, WorkflowError)


def test_scheduler_worker_bounds():
    assert _bounded_worker_count(1) == 1
    assert _bounded_worker_count(0) == 1
    assert _bounded_worker_count(10, configured_limit=2) == 2


def test_scheduler_configs():
    assert _configured_swarm_executor("thread") == "thread"
    assert _configured_swarm_executor("multiprocess") == "process"
    assert _configured_swarm_executor("invalid") == "process"

    assert _configured_worker_limit("4", "ENV_TEST") == 4
    assert _configured_worker_limit("-1", "ENV_TEST") is None

    assert _configured_timeout("12.5", "TIMEOUT_TEST", default=5.0) == 12.5
    assert _configured_timeout("", "TIMEOUT_TEST", default=5.0) == 5.0

    assert _configured_positive_int("8", "INT_TEST", default=2) == 8
    assert _configured_positive_int("-3", "INT_TEST", default=2) == 2


def test_broken_process_pool_detection():
    class CustomBroken(Exception):
        pass

    assert _is_broken_process_pool_error(
        CustomBroken("process pool was terminated abruptly")
    )
    assert not _is_broken_process_pool_error(ValueError("normal error"))


def test_selector_coerce_and_correlation():
    empty_series = _coerce_returns_series(None)
    assert empty_series.empty

    returns_dict = {"2024-01-01": 0.01, "2024-01-02": 0.02}
    s = _coerce_returns_series(returns_dict)
    assert len(s) == 2

    # Invert returns
    inv = _invert_returns(s)
    assert inv.iloc[0] == -0.01

    dates = pd.date_range("2024-01-01", periods=15)
    s1 = pd.Series(range(15), index=dates, dtype=float)
    s2 = pd.Series(range(15), index=dates, dtype=float)
    corr = _series_correlation(s1, s2, min_overlap=5)
    assert corr is not None
    assert pytest.approx(corr) == 1.0


def test_selector_orient_negative_ic():
    factor = {
        "perf_metric": -0.05,
        "metrics": {"ic": -0.05},
        "returns": {"2024-01-01": -0.02},
    }
    oriented = _orient_negative_ic_factor(factor, threshold=0.01)
    assert oriented["perf_metric"] == 0.05
    assert oriented["signal_direction"] == -1
    assert oriented["metrics"]["ic"] == 0.05
    assert oriented["returns"]["2024-01-01"] == 0.02


def test_selector_cull_and_dedupe():
    factors = [
        {"id": "a", "perf_metric": 0.03, "returns": {}},
        {"id": "b", "perf_metric": 0.001, "returns": {}},  # below threshold
        {"id": "c", "perf_metric": -0.04, "returns": {}},  # negative oriented
    ]
    culled = cull_alpha_pool(factors, threshold=0.01)
    ids = [f["id"] for f in culled]
    assert "a" in ids
    assert "b" not in ids
    assert "c" in ids


def test_crossover_selection_and_role():
    f1 = {"id": "f1", "perf_metric": 0.05, "hypothesis": "hyp1", "code": "c1"}
    f2 = {"id": "f2", "perf_metric": 0.03, "hypothesis": "hyp2", "code": "c2"}
    p1, p2 = select_crossover_parents([f2, f1])
    assert p1["id"] == "f1"
    assert p2["id"] == "f2"

    role = build_crossover_role(p1, p2)
    assert "hyp1" in role
    assert "hyp2" in role

    accepted, reason = accept_crossover_result(
        {"perf_metric": 0.001}, threshold=0.01
    )
    assert not accepted
    assert reason == "threshold"


def test_persistence_helpers(tmp_path):
    assert _serialize_returns(None) == {}
    s = pd.Series([0.1, 0.2], index=[pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")])
    serialized = _serialize_returns(s)
    assert "2024-01-01" in list(serialized.keys())[0]

    db_file = tmp_path / "test.db"
    init_portfolio_db(db_file, tmp_path)
    assert db_file.exists()
