from __future__ import annotations

import sqlite3
import time

import pytest

from aiminer.core.task_state import (
    CancellationToken,
    HeartbeatMonitor,
    SwarmRunExecutionTracker,
    TaskCancelledError,
)
from aiminer.manager import PortfolioManager


def test_cancellation_token_basics():
    token = CancellationToken()
    assert not token.is_cancelled()
    token.check_cancelled()  # does not raise

    called = []
    token.add_callback(lambda reason: called.append(reason))

    token.cancel(reason="test cancellation")
    assert token.is_cancelled()
    assert token.reason == "test cancellation"
    assert called == ["test cancellation"]

    with pytest.raises(TaskCancelledError, match="test cancellation"):
        token.check_cancelled()

    # Callbacks added after cancellation should fire immediately
    late_called = []
    token.add_callback(lambda reason: late_called.append(reason))
    assert late_called == ["test cancellation"]


def test_swarm_run_tracker_crud_and_idempotency(tmp_path):
    db_file = tmp_path / "test_aiminer.db"
    tracker = SwarmRunExecutionTracker(db_file)

    # 1. Register new run with idempotency key
    reg, run_id = tracker.register_run(
        "run_001",
        idempotency_key="idemp_key_1",
        config={"model": "gpt-4"},
        total_agents=4,
    )
    assert reg is True
    assert run_id == "run_001"

    # 2. Idempotency test: duplicate call with same key should be rejected
    reg2, ex_id = tracker.register_run(
        "run_002",
        idempotency_key="idemp_key_1",
    )
    assert reg2 is False
    assert ex_id == "run_001"

    # 3. Update heartbeat and progress
    tracker.update_heartbeat("run_001")
    tracker.update_progress(
        "run_001", completed_agents=2, failed_agents=0, factors_count=3
    )

    data = tracker.get_run("run_001")
    assert data is not None
    assert data["status"] == "running"
    assert data["total_agents"] == 4
    assert data["completed_agents"] == 2
    assert data["factors_count"] == 3
    assert data["config"]["model"] == "gpt-4"

    # 4. Complete run
    tracker.complete_run("run_001", metrics={"sharpe": 1.5}, factors_count=5)
    data = tracker.get_run("run_001")
    assert data["status"] == "completed"
    assert data["metrics"]["sharpe"] == 1.5
    assert data["factors_count"] == 5
    assert data["ended_at"] is not None


def test_swarm_run_tracker_failure_and_retry(tmp_path):
    db_file = tmp_path / "test_aiminer.db"
    tracker = SwarmRunExecutionTracker(db_file)

    # Register and fail
    tracker.register_run("run_f1", idempotency_key="retry_key")
    tracker.fail_run("run_f1", error_message="fatal error")

    row = tracker.get_run("run_f1")
    assert row["status"] == "failed"
    assert row["error_message"] == "fatal error"

    # Failed run should allow retry with same idempotency key
    reg, new_id = tracker.register_run(
        "run_f2", idempotency_key="retry_key", total_agents=2
    )
    assert reg is True
    assert new_id == "run_f2"

    row2 = tracker.get_run("run_f2")
    assert row2["status"] == "running"


def test_swarm_run_tracker_cancellation(tmp_path):
    db_file = tmp_path / "test_aiminer.db"
    tracker = SwarmRunExecutionTracker(db_file)

    tracker.register_run("run_c1")
    tracker.cancel_run("run_c1", reason="User stopped run")

    row = tracker.get_run("run_c1")
    assert row["status"] == "cancelled"
    assert row["error_message"] == "User stopped run"


def test_detect_stale_runs(tmp_path):
    db_file = tmp_path / "test_aiminer.db"
    tracker = SwarmRunExecutionTracker(db_file)

    tracker.register_run("stale_run_1")

    # Manually backdate last_heartbeat_at to 2 hours ago
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            UPDATE swarm_runs
            SET last_heartbeat_at = datetime('now', '-2 hours')
            WHERE run_id = 'stale_run_1'
            """
        )

    stale_ids = tracker.detect_stale_runs(heartbeat_timeout_seconds=60.0)
    assert "stale_run_1" in stale_ids

    row = tracker.get_run("stale_run_1")
    assert row["status"] == "failed"
    assert row["error_message"] == "heartbeat_timeout"


def test_heartbeat_monitor_lifecycle(tmp_path):
    db_file = tmp_path / "test_aiminer.db"
    tracker = SwarmRunExecutionTracker(db_file)
    tracker.register_run("run_hb")

    monitor = HeartbeatMonitor(tracker, "run_hb", interval_seconds=0.1)
    monitor.start()
    time.sleep(0.3)
    monitor.stop()

    row = tracker.get_run("run_hb")
    assert row is not None
    assert row["last_heartbeat_at"] is not None


def test_portfolio_manager_cancellation_and_idempotency(tmp_path, monkeypatch):
    db_file = tmp_path / "mgr_test.db"
    tracker = SwarmRunExecutionTracker(db_file)

    cancel_token = CancellationToken()
    cancel_token.cancel("Abort immediately")

    mgr = PortfolioManager(
        db_path=str(db_file),
        cancellation_token=cancel_token,
        execution_tracker=tracker,
        idempotency_key="mgr_key_1",
    )
    # Monkeypatch dispatch_tasks to do nothing
    monkeypatch.setattr(mgr, "dispatch_tasks", lambda **kwargs: None)
    mgr.researchers = [{"agent_id": "a1", "role": "test"}]

    # Run swarm with cancelled token
    pool = mgr.run_swarm(parallel=False)
    assert pool == []

    run_info = tracker.get_run(mgr.run_id)
    assert run_info is not None
    assert run_info["status"] == "cancelled"


def test_portfolio_manager_failure_records_error(tmp_path, monkeypatch):
    db_file = tmp_path / "mgr_fail_test.db"
    tracker = SwarmRunExecutionTracker(db_file)

    mgr = PortfolioManager(
        db_path=str(db_file),
        execution_tracker=tracker,
    )

    def _boom(**kwargs):
        raise RuntimeError("Fatal explosion in swarm execution")

    monkeypatch.setattr(mgr, "dispatch_tasks", _boom)

    with pytest.raises(RuntimeError, match="Fatal explosion"):
        mgr.run_swarm(parallel=False)

    run_info = tracker.get_run(mgr.run_id)
    assert run_info is not None
    assert run_info["status"] == "failed"
    assert "Fatal explosion" in run_info["error_message"]
