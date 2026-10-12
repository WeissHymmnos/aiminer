"""Database initialization, schema migration, checkpoints, and pool persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Optional
import uuid

from loguru import logger
import numpy as np
import scipy.stats

from aiminer.core.agent_checkpoint import (
    ensure_agent_checkpoint_table,
    load_agent_checkpoints,
)
from aiminer.core.alphaeval.multiple_testing import deflated_sharpe_ratio
from aiminer.core.strategy import ensure_strategy_table
from aiminer.pool_io import persist_alpha_pool_rows


def _serialize_returns(returns: Any) -> dict[str, Any]:
    """Convert returns into JSON-safe {iso_date: float} dict."""
    if returns is None or not hasattr(returns, "items"):
        return {}
    out: dict[str, Any] = {}
    for k, v in returns.items():
        try:
            key = k.isoformat() if hasattr(k, "isoformat") else str(k)
            out[key] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _atomic_write_json(path: Path | str, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, target)


def init_portfolio_db(
    db_path: str | Path,
    results_path: Optional[str | Path] = None,
) -> None:
    """Initialize SQLite database schema and tables for factor pool tracking."""
    if results_path is not None:
        Path(results_path).mkdir(parents=True, exist_ok=True)
    db_file = str(db_path)
    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alpha_pool (
                id TEXT PRIMARY KEY,
                role TEXT,
                hypothesis TEXT,
                code TEXT,
                ic REAL,
                rank_ic REAL,
                report_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metrics_json TEXT,
                returns_json TEXT,
                is_effective INTEGER,
                perf_metric REAL,
                selection_score REAL,
                best_strategy_id TEXT,
                best_strategy_metrics_json TEXT,
                execution_style TEXT,
                run_id TEXT,
                agent_id TEXT,
                iteration INTEGER,
                evaluation_mode TEXT,
                evaluation_engine TEXT,
                data_backend TEXT,
                market_mode TEXT,
                market_profile TEXT,
                llm_provider TEXT,
                llm_model TEXT,
                is_simulated INTEGER,
                dsr REAL,
                n_trials INTEGER
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_alpha_timestamp ON "
            "alpha_pool(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_alpha_run_id ON "
            "alpha_pool(run_id)"
        )

        # Idempotent migration for existing columns
        for col, ddl in [
            (
                "metrics_json",
                "ALTER TABLE alpha_pool ADD COLUMN metrics_json TEXT",
            ),
            (
                "returns_json",
                "ALTER TABLE alpha_pool ADD COLUMN returns_json TEXT",
            ),
            (
                "is_effective",
                "ALTER TABLE alpha_pool ADD COLUMN is_effective INTEGER",
            ),
            (
                "perf_metric",
                "ALTER TABLE alpha_pool ADD COLUMN perf_metric REAL",
            ),
            (
                "selection_score",
                "ALTER TABLE alpha_pool ADD COLUMN selection_score REAL",
            ),
            (
                "best_strategy_id",
                "ALTER TABLE alpha_pool ADD COLUMN best_strategy_id TEXT",
            ),
            (
                "best_strategy_metrics_json",
                "ALTER TABLE alpha_pool ADD COLUMN best_strategy_metrics_json TEXT",
            ),
            (
                "execution_style",
                "ALTER TABLE alpha_pool ADD COLUMN execution_style TEXT",
            ),
            ("run_id", "ALTER TABLE alpha_pool ADD COLUMN run_id TEXT"),
            ("agent_id", "ALTER TABLE alpha_pool ADD COLUMN agent_id TEXT"),
            (
                "iteration",
                "ALTER TABLE alpha_pool ADD COLUMN iteration INTEGER",
            ),
            (
                "evaluation_mode",
                "ALTER TABLE alpha_pool ADD COLUMN evaluation_mode TEXT",
            ),
            (
                "evaluation_engine",
                "ALTER TABLE alpha_pool ADD COLUMN evaluation_engine TEXT",
            ),
            (
                "data_backend",
                "ALTER TABLE alpha_pool ADD COLUMN data_backend TEXT",
            ),
            (
                "market_mode",
                "ALTER TABLE alpha_pool ADD COLUMN market_mode TEXT",
            ),
            (
                "market_profile",
                "ALTER TABLE alpha_pool ADD COLUMN market_profile TEXT",
            ),
            (
                "llm_provider",
                "ALTER TABLE alpha_pool ADD COLUMN llm_provider TEXT",
            ),
            (
                "llm_model",
                "ALTER TABLE alpha_pool ADD COLUMN llm_model TEXT",
            ),
            (
                "is_simulated",
                "ALTER TABLE alpha_pool ADD COLUMN is_simulated INTEGER",
            ),
            ("dsr", "ALTER TABLE alpha_pool ADD COLUMN dsr REAL"),
            (
                "n_trials",
                "ALTER TABLE alpha_pool ADD COLUMN n_trials INTEGER",
            ),
        ]:
            try:
                cursor.execute(ddl)
            except sqlite3.OperationalError:
                pass  # column already exists

        # Portfolio table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_pool (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                method TEXT,
                rationale TEXT,
                weights_json TEXT,
                returns_json TEXT,
                diversification_ratio REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    ensure_strategy_table(db_file)
    ensure_agent_checkpoint_table(db_file)


def backfill_alpha_pool_from_json(
    db_path: str | Path, json_path: str | Path
) -> None:
    """One-shot backfill for older databases from JSON backup."""
    target_json = Path(json_path)
    if not target_json.exists():
        return

    with sqlite3.connect(str(db_path)) as conn:
        null_count = conn.execute(
            "SELECT COUNT(*) FROM alpha_pool WHERE metrics_json IS NULL"
        ).fetchone()[0]
    if null_count == 0:
        return

    try:
        with target_json.open("r", encoding="utf-8") as f:
            pool = json.load(f)
    except Exception as e:
        logger.warning(f"[DB Backfill] Failed to read {target_json}: {e}")
        return
    if not isinstance(pool, list) or not pool:
        return

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        for entry in pool:
            fid = entry.get("id")
            if not fid:
                continue
            cursor.execute(
                "SELECT metrics_json FROM alpha_pool WHERE id=?", (fid,)
            )
            row = cursor.fetchone()
            if not row or row[0]:
                continue
            metrics_json = json.dumps(
                entry.get("metrics") or {}, ensure_ascii=False
            )
            returns_json = json.dumps(
                entry.get("returns") or {}, ensure_ascii=False
            )
            is_effective = entry.get("is_effective")
            cursor.execute(
                """UPDATE alpha_pool
                   SET metrics_json=?, returns_json=?, is_effective=?, perf_metric=?
                   WHERE id=?""",
                (
                    metrics_json,
                    returns_json,
                    int(is_effective)
                    if isinstance(is_effective, bool)
                    else is_effective,
                    entry.get("perf_metric"),
                    fid,
                ),
            )
        conn.commit()


def write_alpha_pool_json_backup(
    db_path: str | Path, results_path: str | Path
) -> None:
    """Export SQLite alpha_pool to results/alpha_pool.json backup."""
    output_path = Path(results_path) / "alpha_pool.json"
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, role, hypothesis, code, ic, rank_ic, report_path,
                   timestamp, metrics_json, returns_json, is_effective,
                   perf_metric, selection_score, best_strategy_id,
                   best_strategy_metrics_json, execution_style, run_id,
                   agent_id, iteration, evaluation_mode, evaluation_engine,
                   data_backend, market_mode, market_profile, llm_provider,
                   llm_model, is_simulated, dsr, n_trials
            FROM alpha_pool
            ORDER BY timestamp DESC
            """
        ).fetchall()

    records = []
    for row in rows:
        item = dict(row)
        for source, target in (
            ("metrics_json", "metrics"),
            ("returns_json", "returns"),
            ("best_strategy_metrics_json", "best_strategy_metrics"),
        ):
            raw = item.pop(source, None)
            try:
                item[target] = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, TypeError):
                item[target] = {}
        records.append(item)

    _atomic_write_json(output_path, records)


def recover_checkpoint_results(
    db_path: str | Path,
    run_id: str,
    current_results: list[dict[str, Any]],
    reason: str = "parallel interruption",
) -> list[dict[str, Any]]:
    """Recover best per-agent snapshots after an interrupted parallel swarm."""
    try:
        checkpoints = load_agent_checkpoints(db_path, run_id)
    except Exception as exc:
        logger.warning(f"[Checkpoint] Failed to load checkpoints: {exc}")
        return current_results

    if not checkpoints:
        return current_results

    by_agent = {
        item.get("agent_id") or f"completed_{idx}": item
        for idx, item in enumerate(current_results)
    }
    recovered = 0
    for item in checkpoints:
        agent_id = item.get("agent_id")
        if not agent_id:
            continue
        existing = by_agent.get(agent_id)
        if existing is not None:
            if existing.get("error") and not item.get("error"):
                by_agent[agent_id] = item
                recovered += 1
            continue
        by_agent[agent_id] = item
        recovered += 1

    if recovered:
        logger.warning(
            f"[Checkpoint] Recovered {recovered} best agent result(s) "
            f"from checkpoint after {reason}."
        )
    return list(by_agent.values())


def persist_alpha_factors(
    db_path: str | Path,
    results_path: str | Path,
    factors: list[dict[str, Any]],
    run_id: str,
    trial_sharpes: Optional[list[float]] = None,
    n_trials: int = 0,
) -> list[dict[str, Any]]:
    """Calculate multiple-testing DSR and persist factors to DB and JSON."""
    factors_to_persist = list(factors)
    if not factors_to_persist:
        return []

    sharpes = trial_sharpes or []
    effective_n_trials = max(
        n_trials,
        len(sharpes),
        len(factors_to_persist),
        1,
    )

    for factor in factors_to_persist:
        if factor.get("n_trials") is None:
            factor["n_trials"] = effective_n_trials

        if factor.get("dsr") is None:
            metrics = factor.get("metrics") or {}
            sr = metrics.get("sharpe")
            if sr is None:
                sr = factor.get("perf_metric", 0.0)
            try:
                sr_val = float(sr) if sr is not None else 0.0
            except (ValueError, TypeError):
                sr_val = 0.0

            returns = factor.get("returns") or {}
            if isinstance(returns, dict) and len(returns) >= 4:
                try:
                    rets = np.asarray(list(returns.values()), dtype=float)
                    rets = rets[np.isfinite(rets)]
                except (ValueError, TypeError):
                    rets = np.array([], dtype=float)
            else:
                rets = np.array([], dtype=float)

            if len(rets) >= 4:
                sample_len = len(rets)
                skew = float(scipy.stats.skew(rets))
                kurt = float(scipy.stats.kurtosis(rets, fisher=False))
            else:
                sample_len = 252
                skew = 0.0
                kurt = 3.0

            factor_n = factor.get("n_trials", effective_n_trials)
            trials = sharpes if sharpes else [sr_val]
            factor["dsr"] = deflated_sharpe_ratio(
                estimated_sharpe=sr_val,
                var_sharpe_or_trials=trials,
                n_trials=factor_n,
                skewness=skew,
                kurtosis=kurt,
                sample_length=sample_len,
            )

    persist_alpha_pool_rows(
        db_path,
        results_path,
        factors_to_persist,
        run_id=run_id,
    )
    return factors_to_persist
