from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.agent_result import state_to_agent_result


def ensure_agent_checkpoint_table(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_checkpoints (
                run_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                role TEXT,
                iteration INTEGER,
                payload_json TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, agent_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_run_id "
            "ON agent_checkpoints(run_id)"
        )
        conn.commit()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return _json_safe(value.to_dict(orient="index"))
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, (np.ndarray,)):
        return _json_safe(value.tolist())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def persist_agent_checkpoint(
    db_path: str | Path,
    state: dict,
    *,
    settings: Any | None = None,
) -> None:
    result = state_to_agent_result(
        state,
        settings=settings,
        role_prompt=state.get("role_prompt"),
        run_id=state.get("run_id"),
        agent_id=state.get("agent_id"),
        max_iterations=state.get("max_iterations"),
    )
    if not result.get("run_id") or not result.get("agent_id"):
        return
    if not result.get("code") or not result.get("metrics"):
        return

    ensure_agent_checkpoint_table(db_path)
    payload = _json_safe(result)
    payload_json = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    with sqlite3.connect(str(db_path), timeout=30) as conn:
        conn.execute(
            """
            INSERT INTO agent_checkpoints
                (run_id, agent_id, role, iteration, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(run_id, agent_id) DO UPDATE SET
                role=excluded.role,
                iteration=excluded.iteration,
                payload_json=excluded.payload_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                result.get("run_id"),
                result.get("agent_id"),
                result.get("role"),
                result.get("iteration"),
                payload_json,
            ),
        )
        conn.commit()


def load_agent_checkpoints(db_path: str | Path, run_id: str) -> list[dict]:
    ensure_agent_checkpoint_table(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM agent_checkpoints
            WHERE run_id=?
            ORDER BY updated_at DESC
            """,
            (run_id,),
        ).fetchall()

    results = []
    for (raw_payload,) in rows:
        try:
            payload = json.loads(raw_payload)
        except Exception:
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return results
