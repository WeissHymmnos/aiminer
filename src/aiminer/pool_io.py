"""Public load/persist helpers for alpha_pool. No SummaryAgent import."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

def _serialize_returns(returns: Any) -> dict[str, Any]:
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


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


_CREATE_ALPHA_POOL = """
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
    is_simulated INTEGER
)
"""


def ensure_alpha_pool_schema(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_CREATE_ALPHA_POOL)


def load_alpha_pool_rows(db_path: str | Path) -> list[dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        return []
    ensure_alpha_pool_schema(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM alpha_pool ORDER BY timestamp DESC").fetchall()
        except sqlite3.OperationalError:
            return []
    records: list[dict[str, Any]] = []
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
            except Exception:
                item[target] = {}
        records.append(item)
    return records


def write_alpha_pool_json_backup(db_path: str | Path, results_path: str | Path) -> None:
    output_path = Path(results_path) / "alpha_pool.json"
    records = load_alpha_pool_rows(db_path)
    _atomic_write_json(output_path, records)


def persist_alpha_pool_rows(
    db_path: str | Path,
    results_path: str | Path,
    factors: list[dict[str, Any]],
    *,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    if not factors:
        return []
    db = Path(db_path)
    results = Path(results_path)
    results.mkdir(parents=True, exist_ok=True)
    ensure_alpha_pool_schema(db)
    reports = results / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    persisted: list[dict[str, Any]] = []
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        for factor in factors:
            factor = dict(factor)
            factor.pop("_normalized_return_series", None)
            if not factor.get("id"):
                factor["id"] = f"alpha_{uuid.uuid4().hex[:8]}"
            report_path = factor.get("report_path")
            if not report_path:
                synth = reports / f"synthetic_{factor['id']}.md"
                if not synth.exists():
                    synth.write_text(
                        f"# {factor.get('hypothesis') or factor['id']}\n",
                        encoding="utf-8",
                    )
                report_path = str(synth)
                factor["report_path"] = report_path
            returns_dict = factor.get("returns") or {}
            metrics = factor.get("metrics") or {}
            cursor.execute(
                """
                INSERT OR REPLACE INTO alpha_pool
                    (id, role, hypothesis, code, ic, rank_ic, report_path,
                     metrics_json, returns_json, is_effective, perf_metric,
                     selection_score, best_strategy_id, best_strategy_metrics_json, execution_style,
                     run_id, agent_id, iteration, evaluation_mode,
                     evaluation_engine, data_backend, market_mode, market_profile,
                     llm_provider, llm_model, is_simulated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    factor.get("id"),
                    factor.get("role"),
                    factor.get("hypothesis"),
                    factor.get("code"),
                    metrics.get("information_coefficient", factor.get("perf_metric", 0.0)),
                    metrics.get("rank_ic", 0.0),
                    report_path,
                    json.dumps(metrics, ensure_ascii=False),
                    json.dumps(_serialize_returns(returns_dict), ensure_ascii=False)
                    if not isinstance(returns_dict, dict)
                    else json.dumps(returns_dict, ensure_ascii=False),
                    int(bool(factor.get("is_effective"))),
                    factor.get("perf_metric"),
                    factor.get("selection_score"),
                    factor.get("best_strategy_id"),
                    json.dumps(factor.get("best_strategy_metrics") or {}, ensure_ascii=False),
                    factor.get("execution_style"),
                    factor.get("run_id", run_id),
                    factor.get("agent_id"),
                    factor.get("iteration"),
                    factor.get("evaluation_mode"),
                    factor.get("evaluation_engine"),
                    factor.get("data_backend"),
                    factor.get("market_mode"),
                    factor.get("market_profile"),
                    factor.get("llm_provider"),
                    factor.get("llm_model"),
                    int(factor.get("is_simulated", False)),
                ),
            )
            persisted.append(factor)
            _notify_catalog("pool", factor)
        conn.commit()
    write_alpha_pool_json_backup(db, results)
    return persisted


def _notify_catalog(kind: str, payload: dict[str, Any]) -> None:
    if os.environ.get("FINAINCE_CATALOG", "1") == "0":
        return
    try:
        from finaince.catalog.hooks import accept_library_entry, accept_pool_row
    except ImportError:
        return
    if kind == "pool":
        accept_pool_row(payload)
    else:
        accept_library_entry(**payload)
