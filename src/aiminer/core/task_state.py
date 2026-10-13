from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable

from loguru import logger


class TaskCancelledError(Exception):
    """Raised when a running task or swarm is cancelled."""


class CancellationToken:
    """Thread-safe cooperative cancellation token."""

    def __init__(self) -> None:
        self._is_cancelled = threading.Event()
        self._reason: str = ""
        self._callbacks: list[Callable[[str], None]] = []
        self._lock = threading.Lock()

    def cancel(self, reason: str = "Task was cancelled") -> None:
        with self._lock:
            if not self._is_cancelled.is_set():
                self._reason = reason
                self._is_cancelled.set()
                for cb in self._callbacks:
                    try:
                        cb(reason)
                    except Exception as exc:
                        logger.warning(f"Cancellation callback failed: {exc}")

    def is_cancelled(self) -> bool:
        return self._is_cancelled.is_set()

    def check_cancelled(self) -> None:
        if self._is_cancelled.is_set():
            raise TaskCancelledError(self._reason or "Task was cancelled")

    @property
    def reason(self) -> str:
        return self._reason

    def add_callback(self, cb: Callable[[str], None]) -> None:
        with self._lock:
            if self._is_cancelled.is_set():
                cb(self._reason)
            else:
                self._callbacks.append(cb)


class SwarmRunExecutionTracker:
    """SQLite-backed execution state tracker and idempotency coordinator."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.ensure_tables()

    def ensure_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS swarm_runs (
                    run_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    status TEXT NOT NULL,
                    total_agents INTEGER DEFAULT 0,
                    completed_agents INTEGER DEFAULT 0,
                    failed_agents INTEGER DEFAULT 0,
                    factors_count INTEGER DEFAULT 0,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at DATETIME,
                    error_message TEXT,
                    config_json TEXT,
                    metrics_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_swarm_runs_idemp "
                "ON swarm_runs(idempotency_key)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_swarm_runs_status "
                "ON swarm_runs(status)"
            )
            conn.commit()

    def register_run(
        self,
        run_id: str,
        *,
        idempotency_key: str | None = None,
        config: dict[str, Any] | None = None,
        total_agents: int = 0,
    ) -> tuple[bool, str]:
        """Register a new run, enforcing idempotency if key is supplied.

        Returns:
            (registered, active_run_id)
        """
        cfg_str = json.dumps(config or {}, ensure_ascii=False, default=str)
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if idempotency_key:
                cursor.execute(
                    "SELECT run_id, status FROM swarm_runs "
                    "WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                existing = cursor.fetchone()
                if existing:
                    ex_id = existing["run_id"]
                    ex_status = existing["status"]
                    if ex_status in {"running", "completed"}:
                        return False, ex_id

                    # If previous attempt failed or cancelled, reuse/update
                    cursor.execute(
                        """
                        UPDATE swarm_runs
                        SET run_id = ?,
                            status = 'running',
                            total_agents = ?,
                            completed_agents = 0,
                            failed_agents = 0,
                            started_at = CURRENT_TIMESTAMP,
                            last_heartbeat_at = CURRENT_TIMESTAMP,
                            ended_at = NULL,
                            error_message = NULL,
                            config_json = ?
                        WHERE idempotency_key = ?
                        """,
                        (run_id, total_agents, cfg_str, idempotency_key),
                    )
                    conn.commit()
                    return True, run_id

            cursor.execute(
                """
                INSERT INTO swarm_runs
                    (run_id, idempotency_key, status, total_agents,
                     config_json, started_at, last_heartbeat_at)
                VALUES (?, ?, 'running', ?, ?, CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP)
                ON CONFLICT(run_id) DO UPDATE SET
                    status='running',
                    idempotency_key=excluded.idempotency_key,
                    total_agents=excluded.total_agents,
                    config_json=excluded.config_json,
                    started_at=CURRENT_TIMESTAMP,
                    last_heartbeat_at=CURRENT_TIMESTAMP,
                    ended_at=NULL,
                    error_message=NULL
                """,
                (run_id, idempotency_key, total_agents, cfg_str),
            )
            conn.commit()
            return True, run_id

    def update_heartbeat(self, run_id: str) -> None:
        """Update last heartbeat timestamp for the specified run."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                """
                UPDATE swarm_runs
                SET last_heartbeat_at = CURRENT_TIMESTAMP
                WHERE run_id = ?
                """,
                (run_id,),
            )
            conn.commit()

    def update_progress(
        self,
        run_id: str,
        *,
        completed_agents: int | None = None,
        failed_agents: int | None = None,
        factors_count: int | None = None,
    ) -> None:
        """Update intermediate progress counters for an active run."""
        fields: list[str] = ["last_heartbeat_at = CURRENT_TIMESTAMP"]
        params: list[Any] = []
        if completed_agents is not None:
            fields.append("completed_agents = ?")
            params.append(completed_agents)
        if failed_agents is not None:
            fields.append("failed_agents = ?")
            params.append(failed_agents)
        if factors_count is not None:
            fields.append("factors_count = ?")
            params.append(factors_count)

        params.append(run_id)
        sql = f"UPDATE swarm_runs SET {', '.join(fields)} WHERE run_id = ?"
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(sql, params)
            conn.commit()

    def complete_run(
        self,
        run_id: str,
        *,
        metrics: dict[str, Any] | None = None,
        factors_count: int | None = None,
    ) -> None:
        """Mark a run as successfully completed."""
        m_json = json.dumps(metrics or {}, ensure_ascii=False, default=str)
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            if factors_count is not None:
                conn.execute(
                    """
                    UPDATE swarm_runs
                    SET status = 'completed',
                        metrics_json = ?,
                        factors_count = ?,
                        ended_at = CURRENT_TIMESTAMP
                    WHERE run_id = ?
                    """,
                    (m_json, factors_count, run_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE swarm_runs
                    SET status = 'completed',
                        metrics_json = ?,
                        ended_at = CURRENT_TIMESTAMP
                    WHERE run_id = ?
                    """,
                    (m_json, run_id),
                )
            conn.commit()

    def fail_run(self, run_id: str, error_message: str | None = None) -> None:
        """Mark a run as failed with an error message."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                """
                UPDATE swarm_runs
                SET status = 'failed',
                    error_message = ?,
                    ended_at = CURRENT_TIMESTAMP
                WHERE run_id = ?
                """,
                (error_message, run_id),
            )
            conn.commit()

    def cancel_run(self, run_id: str, reason: str | None = None) -> None:
        """Mark a run as cancelled."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                """
                UPDATE swarm_runs
                SET status = 'cancelled',
                    error_message = ?,
                    ended_at = CURRENT_TIMESTAMP
                WHERE run_id = ?
                """,
                (reason or "Cancelled by user", run_id),
            )
            conn.commit()

    def detect_stale_runs(
        self, heartbeat_timeout_seconds: float = 60.0
    ) -> list[str]:
        """Detect and fail runs whose heartbeats have stalled beyond timeout."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT run_id,
                       (strftime('%s', 'now') -
                        strftime('%s', last_heartbeat_at)) AS elapsed
                FROM swarm_runs
                WHERE status = 'running'
                """
            )
            rows = cursor.fetchall()
            stale_ids = [
                r["run_id"]
                for r in rows
                if (r["elapsed"] or 0) > heartbeat_timeout_seconds
            ]

            if stale_ids:
                placeholders = ",".join("?" for _ in stale_ids)
                cursor.execute(
                    f"""
                    UPDATE swarm_runs
                    SET status = 'failed',
                        error_message = 'heartbeat_timeout',
                        ended_at = CURRENT_TIMESTAMP
                    WHERE run_id IN ({placeholders})
                    """,
                    stale_ids,
                )
                conn.commit()
            return stale_ids

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve run state dictionary by run_id."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM swarm_runs WHERE run_id = ?", (run_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            if result.get("config_json"):
                try:
                    result["config"] = json.loads(result["config_json"])
                except Exception:
                    result["config"] = {}
            if result.get("metrics_json"):
                try:
                    result["metrics"] = json.loads(result["metrics_json"])
                except Exception:
                    result["metrics"] = {}
            return result


class HeartbeatMonitor:
    """Daemon thread for sending periodic heartbeats for a running swarm."""

    def __init__(
        self,
        tracker: SwarmRunExecutionTracker,
        run_id: str,
        interval_seconds: float = 5.0,
    ):
        self.tracker = tracker
        self.run_id = run_id
        self.interval = max(0.5, float(interval_seconds))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"HeartbeatMonitor-{self.run_id[:8]}",
            daemon=True,
        )
        self._thread.start()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.tracker.update_heartbeat(self.run_id)
            except Exception as exc:
                logger.warning(f"Heartbeat failed for {self.run_id}: {exc}")
            time.sleep(self.interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
