import asyncio
import importlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest
from core.strategy import persist_strategy_result
from fastapi import HTTPException
from fastapi.testclient import TestClient


os.environ["AIMINER_DISABLE_AUTH"] = "true"

import api  # noqa: E402


def _module():
    return importlib.reload(api)


def _prepare_db(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir / "alpha_miner.db"


class _AliveProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self.join_calls = []

    def is_alive(self) -> bool:
        return True

    def join(self, timeout=None) -> None:
        self.join_calls.append(timeout)


class _ExitedProcess:
    def __init__(self, exitcode: int = 0):
        self.exitcode = exitcode
        self.pid = 0

    def join(self) -> None:
        return None


class _QueueStub:
    def __init__(self):
        self.items = []

    def put(self, payload, timeout=None):
        self.items.append((payload, timeout))


class _PsutilProcessStub:
    def __init__(self, pid: int, create_time: float = 1234.0, status: str = "sleeping"):
        self.pid = pid
        self._create_time = create_time
        self._status = status

    def is_running(self) -> bool:
        return True

    def status(self) -> str:
        return self._status

    def create_time(self) -> float:
        return self._create_time


def test_results_endpoint_returns_paginated_shape():
    mod = _module()
    payload = mod.get_results(run_id=None, offset=0, limit=10)
    assert {"items", "total", "offset", "limit", "next_offset"} <= set(payload.keys())
    assert payload["limit"] == 10
    if payload["items"]:
        assert {"selection_score", "best_strategy_id"} <= set(payload["items"][0].keys())


def test_results_endpoint_legacy_alpha_pool_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = _prepare_db(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE alpha_pool (
                id TEXT PRIMARY KEY,
                role TEXT,
                hypothesis TEXT,
                code TEXT,
                ic REAL,
                rank_ic REAL,
                is_effective INTEGER,
                perf_metric REAL,
                report_path TEXT,
                timestamp TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO alpha_pool (
                id, role, hypothesis, code, ic, rank_ic, is_effective, perf_metric, report_path, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "alpha_legacy",
                "researcher",
                "legacy hypothesis",
                "rank(close)",
                0.11,
                0.07,
                1,
                1.5,
                "legacy.md",
                "2024-01-01T00:00:00",
            ),
        )
        conn.commit()

    mod = _module()
    payload = mod.get_results(run_id=None, offset=0, limit=10)

    assert payload["items"][0]["id"] == "alpha_legacy"
    assert "selection_score" in payload["items"][0]
    assert payload["items"][0]["selection_score"] is None
    assert payload["items"][0]["best_strategy_id"] is None


def test_wiki_index_returns_paginated_shape():
    mod = _module()
    payload = mod.wiki_index(offset=0, limit=10)
    assert {"items", "total", "offset", "limit", "next_offset"} <= set(payload.keys())
    assert payload["limit"] == 10


def test_wiki_graph_returns_nodes_and_edges():
    mod = _module()
    payload = mod.wiki_graph()
    assert "nodes" in payload
    assert "edges" in payload


def test_swarm_status_available_when_auth_disabled():
    mod = _module()
    actor = mod.Actor(identity="auth-disabled")
    payload = mod.swarm_status(actor=actor)
    assert "running_count" in payload


def test_missing_auth_token_defaults_to_auth_disabled(monkeypatch):
    monkeypatch.delenv("AIMINER_DISABLE_AUTH", raising=False)
    monkeypatch.delenv("AIMINER_AUTH_TOKEN", raising=False)

    mod = _module()
    actor = mod._require_actor(credentials=None, request=None)

    assert actor.identity == "auth-disabled"
    assert mod.AUTH_DISABLED is True


def test_disconnected_remote_maps_to_service_unavailable():
    mod = _module()
    exc = RuntimeError("Disconnected from the remote server")

    http_exc = mod._service_error(exc, "backtest failed")

    assert http_exc.status_code == 503
    assert "RiceQuant disconnected" in http_exc.detail


def test_swarm_logs_tail_returns_recent_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "results" / "swarm_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "run_1.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_1.jsonl").write_text(
        "\n".join(
            json.dumps({"message": f"log-{index}", "timestamp": f"00:00:0{index}"})
            for index in range(5)
        ),
        encoding="utf-8",
    )

    mod = _module()
    actor = mod.Actor(identity="auth-disabled")
    payload = mod.get_swarm_run_logs("run_1", offset=0, limit=2, tail=True, actor=actor)

    assert [item["message"] for item in payload["items"]] == ["log-3", "log-4"]
    assert payload["offset"] == 3
    assert payload["next_offset"] == 5


def test_swarm_logs_tail_ignores_corrupt_recent_lines(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "results" / "swarm_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "run_2.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_2.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"message": "log-0", "timestamp": "00:00:00"}),
                json.dumps({"message": "log-1", "timestamp": "00:00:01"}),
                json.dumps({"message": "log-2", "timestamp": "00:00:02"}),
                "{broken-json",
                json.dumps({"message": "log-4", "timestamp": "00:00:04"}),
            ]
        ),
        encoding="utf-8",
    )

    mod = _module()
    actor = mod.Actor(identity="auth-disabled")
    payload = mod.get_swarm_run_logs("run_2", offset=0, limit=2, tail=True, actor=actor)

    assert [item["message"] for item in payload["items"]] == ["log-4"]
    assert payload["offset"] == 3
    assert payload["next_offset"] == 5


def test_stop_swarm_marks_run_stopping_while_process_is_alive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_stop_live"
    mod._write_run_manifest(
        run_id,
        {
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 4321,
        },
    )
    run_state = mod.RunState(
        run_id=run_id,
        process=_AliveProcess(pid=4321),
        queue=_QueueStub(),
        listener_thread=None,
        config={},
    )
    with mod.state.lock:
        mod.state.runs[run_id] = run_state
    stopped_pids = []
    monkeypatch.setattr(mod, "_stop_process_tree", lambda pid: stopped_pids.append(pid))

    actor = mod.Actor(identity="auth-disabled")
    response = mod.stop_swarm(run_id, actor=actor)
    detail = mod.get_swarm_run(run_id, actor=actor)
    manifest = mod._load_json(mod._manifest_path(run_id))

    assert response["status"] == "stopping"
    assert stopped_pids == [4321]
    assert manifest["status"] == "stopping"
    assert manifest.get("ended_at") is None
    assert detail["status"] == "stopping"
    assert detail["is_active"] is True


def test_wait_run_process_finalizes_stop_requested_run_as_stopped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_stop_exit"
    mod._write_run_manifest(
        run_id,
        {
            "status": "stopping",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 9876,
        },
    )

    mod._wait_run_process(run_id, _ExitedProcess(exitcode=0), _QueueStub())

    actor = mod.Actor(identity="auth-disabled")
    detail = mod.get_swarm_run(run_id, actor=actor)
    logs = mod.get_swarm_run_logs(run_id, offset=0, limit=10, tail=False, actor=actor)

    assert detail["status"] == "stopped"
    assert detail["is_active"] is False
    assert detail["ended_at"] is not None
    assert any(item.get("status") == "stopped" for item in logs["items"])


def test_shutdown_event_stops_active_swarm_process(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_shutdown_live"
    mod._write_run_manifest(
        run_id,
        {
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 2468,
        },
    )
    process = _AliveProcess(pid=2468)
    run_state = mod.RunState(
        run_id=run_id,
        process=process,
        queue=_QueueStub(),
        listener_thread=None,
        config={},
    )
    with mod.state.lock:
        mod.state.runs[run_id] = run_state
    stopped_pids = []
    monkeypatch.setattr(mod, "_stop_process_tree", lambda pid: stopped_pids.append(pid))

    mod._shutdown_active_swarm_runs()
    detail = mod._load_json(mod._manifest_path(run_id))

    assert stopped_pids == [2468]
    assert process.join_calls == [5]
    assert detail["status"] == "stopped"
    assert detail["ended_at"] is not None
    assert run_id not in mod.state.runs


def test_stale_starting_run_is_recovered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIMINER_STALE_STARTING_SECONDS", "1")
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_stale_starting"
    stale_time = (datetime.utcnow() - timedelta(seconds=10)).isoformat(timespec="seconds")
    mod._write_run_manifest(
        run_id,
        {
            "status": "starting",
            "created_at": stale_time,
            "started_at": stale_time,
        },
    )

    actor = mod.Actor(identity="auth-disabled")
    detail = mod.get_swarm_run(run_id, actor=actor)

    assert detail["status"] == "failed"
    assert detail["is_active"] is False
    assert detail["ended_at"] is not None
    assert "stale starting run" in detail["failure_reason"]


def test_delete_run_blocks_manifest_active_process_after_api_restart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_restart_active"
    create_time = 4321.0
    mod._write_run_manifest(
        run_id,
        {
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 24680,
            "process_create_time": create_time,
        },
    )
    mod._log_path(run_id).write_text('{"message":"still running"}\n', encoding="utf-8")
    monkeypatch.setattr(
        mod.psutil,
        "Process",
        lambda pid: _PsutilProcessStub(pid, create_time=create_time),
    )

    actor = mod.Actor(identity="auth-disabled")
    with pytest.raises(HTTPException) as exc_info:
        mod.delete_swarm_run(run_id, actor=actor)

    assert exc_info.value.status_code == 409
    assert mod._manifest_path(run_id).exists()
    assert mod._log_path(run_id).exists()


def test_swarm_status_counts_manifest_active_process_after_api_restart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    create_time = 111.0
    mod._write_run_manifest(
        "run_manifest_active",
        {
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 13579,
            "process_create_time": create_time,
        },
    )
    monkeypatch.setattr(
        mod.psutil,
        "Process",
        lambda pid: _PsutilProcessStub(pid, create_time=create_time),
    )

    payload = mod.swarm_status(actor=mod.Actor(identity="auth-disabled"))

    assert payload["running_count"] == 1
    assert payload["active_run_ids"] == ["run_manifest_active"]


def test_running_filter_excludes_inactive_running_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_inactive_running"
    mod._write_run_manifest(
        run_id,
        {
            "status": "running",
            "started_at": "2024-01-01T00:00:00",
            "process_pid": 999999,
            "process_create_time": 10.0,
        },
    )

    def _missing_process(pid):
        raise mod.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(mod.psutil, "Process", _missing_process)
    actor = mod.Actor(identity="auth-disabled")

    running = mod.list_swarm_runs(status_filter="running", offset=0, limit=10, actor=actor)
    all_runs = mod.list_swarm_runs(status_filter=None, offset=0, limit=10, actor=actor)

    assert running["items"] == []
    assert all_runs["items"][0]["run_id"] == run_id
    assert all_runs["items"][0]["status"] == "stopped"
    assert all_runs["items"][0]["is_active"] is False


def test_run_manifest_writes_are_atomic_and_run_locked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()
    mod.SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "run_manifest_lock"
    mod._write_run_manifest(run_id, {"status": "starting"})

    threads = [
        threading.Thread(
            target=mod._write_run_manifest,
            args=(run_id, {f"key_{index}": index}),
        )
        for index in range(12)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    manifest = mod._load_json(mod._manifest_path(run_id))

    assert manifest["status"] == "starting"
    for index in range(12):
        assert manifest[f"key_{index}"] == index


def test_swarm_config_rejects_invalid_enum_before_route_creates_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mod = _module()

    with TestClient(mod.app) as client:
        response = client.post(
            "/api/swarm/runs",
            json={
                "iterations": 1,
                "mode": "ricequant",
                "data_backend": "not-a-backend",
                "engine": "polars",
                "roles": ["researcher"],
            },
        )

    assert response.status_code == 422
    assert not mod.SWARM_RUN_DIR.exists() or not list(mod.SWARM_RUN_DIR.glob("run_*.json"))


def test_runtime_request_models_normalize_compatible_aliases():
    mod = _module()

    config = mod.SwarmConfig.model_validate(
        {
            "iterations": 1,
            "evaluation_mode": "rq",
            "data_backend": "csv",
            "evaluation_engine": "pl",
            "roles": "researcher",
            "market_mode": "multi",
            "market_profile": "cn",
            "market_profiles": "cn,us",
            "local_data_path": "/tmp/data",
            "local_data_layout": "contracts",
        }
    )

    assert config.mode == "ricequant"
    assert config.data_backend == "local"
    assert config.engine == "polars"
    assert config.roles == ["researcher"]
    assert config.market_mode == "batch"
    assert config.market_profile == "cn_stock"
    assert config.market_profiles == ["cn_stock", "us_stock"]
    assert config.local_data_layout == "instrument_files"


def test_delete_strategy_handles_missing_strategy_table(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = _prepare_db(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE unrelated (id TEXT PRIMARY KEY)")
        conn.commit()

    mod = _module()
    actor = mod.Actor(identity="auth-disabled")

    with pytest.raises(HTTPException) as exc_info:
        mod.delete_strategy("strategy_missing", actor=actor)

    assert exc_info.value.status_code == 404

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "strategy_backtests" in tables


def test_frontend_fallback_uses_frontend_dist_build_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    frontend_dist = tmp_path / "frontend" / "dist"
    frontend_dist.mkdir(parents=True)
    html = "<!doctype html><html><body>frontend ok</body></html>"
    (frontend_dist / "index.html").write_text(html, encoding="utf-8")

    mod = _module()
    response = mod.frontend_fallback("wiki")

    assert response.body.decode("utf-8") == html


def test_strategy_endpoints_surface_template_name_and_rationale(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    persist_strategy_result(
        tmp_path / "results" / "alpha_miner.db",
        {
            "strategy_id": "strategy_seed_1",
            "label": "Seed Strategy",
            "template_name": "cs_top_bottom",
            "rationale": "Agent prefers cross-sectional long-short execution.",
            "run_type": "strategy_backtest",
            "expression": "rank(delta(close, 5))",
            "strategy_config": {
                "label": "Seed Strategy",
                "strategy_mode": "cross_sectional",
                "signal_source": "expression",
                "direction": "long_short",
                "selection_rule": "top_bottom_n",
            },
            "metrics": {"sharpe": 1.23},
            "daily_returns": {"2024-01-01": 0.01},
            "positions": {},
            "trade_stats": {},
            "chart_paths": {},
            "market": "cn_stock",
            "engine": "polars",
            "ran_at": "2024-01-01T00:00:00",
            "run_id": "run_seed_1",
            "source_factor_id": "alpha_1",
            "candidate_rank": 1,
            "selection_score": 0.42,
            "is_primary": True,
            "market_profile": "cn_stock",
            "data_backend": "local",
        },
    )

    mod = _module()
    listing = mod.get_strategies(run_id=None, offset=0, limit=10)
    detail = mod.get_strategy("strategy_seed_1")

    assert listing["items"][0]["template_name"] == "cs_top_bottom"
    assert listing["items"][0]["rationale"] == "Agent prefers cross-sectional long-short execution."
    assert detail["template_name"] == "cs_top_bottom"
    assert detail["rationale"] == "Agent prefers cross-sectional long-short execution."


def test_strategy_endpoints_support_legacy_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = _prepare_db(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE strategy_backtests (
                strategy_id TEXT PRIMARY KEY,
                label TEXT,
                run_type TEXT,
                strategy_mode TEXT,
                signal_source TEXT,
                expression_json TEXT,
                strategy_config_json TEXT,
                metrics_json TEXT,
                daily_returns_json TEXT,
                positions_json TEXT,
                trade_stats_json TEXT,
                chart_paths_json TEXT,
                market TEXT,
                engine TEXT,
                ran_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO strategy_backtests (
                strategy_id, label, run_type, strategy_mode, signal_source,
                expression_json, strategy_config_json, metrics_json,
                daily_returns_json, positions_json, trade_stats_json,
                chart_paths_json, market, engine, ran_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "strategy_legacy",
                "Legacy Strategy",
                "strategy_backtest",
                "cross_sectional",
                "expression",
                json.dumps({"expression": "rank(close)"}),
                json.dumps({"label": "Legacy Strategy"}),
                json.dumps({"sharpe": 1.0}),
                json.dumps({"2024-01-01": 0.01}),
                json.dumps({}),
                json.dumps({}),
                json.dumps({}),
                "cn_stock",
                "polars",
                "2024-01-01T00:00:00",
            ),
        )
        conn.commit()

    mod = _module()
    listing = mod.get_strategies(run_id=None, offset=0, limit=10)
    detail = mod.get_strategy("strategy_legacy")

    assert listing["items"][0]["strategy_id"] == "strategy_legacy"
    assert listing["items"][0]["template_name"] is None
    assert listing["items"][0]["selection_score"] is None
    assert detail["strategy_id"] == "strategy_legacy"
    assert detail.get("template_name") is None
    assert detail["expression"] == "rank(close)"


def test_startup_event_migrates_alpha_and_strategy_tables(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = _prepare_db(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE alpha_pool (
                id TEXT PRIMARY KEY,
                role TEXT,
                hypothesis TEXT,
                code TEXT,
                ic REAL,
                rank_ic REAL,
                is_effective INTEGER,
                perf_metric REAL,
                report_path TEXT,
                timestamp TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE strategy_backtests (
                strategy_id TEXT PRIMARY KEY,
                label TEXT,
                run_type TEXT,
                strategy_mode TEXT,
                signal_source TEXT,
                expression_json TEXT,
                strategy_config_json TEXT,
                metrics_json TEXT,
                daily_returns_json TEXT,
                positions_json TEXT,
                trade_stats_json TEXT,
                chart_paths_json TEXT,
                market TEXT,
                engine TEXT,
                ran_at TEXT
            )
            """
        )
        conn.commit()

    mod = _module()
    asyncio.run(mod.startup_event())

    with sqlite3.connect(db_path) as conn:
        alpha_columns = {row[1] for row in conn.execute("PRAGMA table_info(alpha_pool)").fetchall()}
        strategy_columns = {row[1] for row in conn.execute("PRAGMA table_info(strategy_backtests)").fetchall()}

    assert {"selection_score", "best_strategy_id", "execution_style"} <= alpha_columns
    assert {"template_name", "rationale", "run_id", "selection_score"} <= strategy_columns
