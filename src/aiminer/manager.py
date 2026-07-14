# --- Imports & Logging Setup ---

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import argparse
import pandas as pd
from loguru import logger
import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
from dotenv import load_dotenv
import multiprocessing
import threading
import time
import random

import sqlite3
import json
import uuid

from aiminer.sub_agent import AlphaResearcher
from aiminer.agents.summary_agent import SummaryAgent
from aiminer.agents.portfolio_agent import PortfolioAgent
from aiminer.core.agent_checkpoint import (
    ensure_agent_checkpoint_table,
    load_agent_checkpoints,
)
from aiminer.core.portfolio import construct_portfolio
from aiminer.core.alphaeval.rq_eval import init_rq_auth
from aiminer.core.constants import IC_CULL_THRESHOLD
from aiminer.core.runtime import log_context, new_agent_id, new_run_id
from aiminer.core.settings import build_settings
from aiminer.core.strategy import (
    ensure_strategy_table,
    persist_strategy_result,
    selection_score,
    strategy_templates,
)


# --- Worker Process Utilities ---

_WORKER_LOG_QUEUE = None


def _init_worker_context(log_queue=None):
    global _WORKER_LOG_QUEUE
    _WORKER_LOG_QUEUE = log_queue


# Global entry point for multiprocessing
def run_agent_task(kwargs):
    task_kwargs = dict(kwargs)
    if _WORKER_LOG_QUEUE is not None and "log_queue" not in task_kwargs:
        task_kwargs["log_queue"] = _WORKER_LOG_QUEUE
    # Add a small random jitter to avoid simultaneous DB file access
    time.sleep(random.uniform(0.1, 1.0))
    agent = AlphaResearcher(**task_kwargs)
    return agent.run()


def _forward_worker_logs(worker_log_queue, parent_log_queue):
    """Bridge log records from ProcessPool workers back to the swarm log queue.

    In spawn mode, a raw multiprocessing.Queue cannot be passed as task args
    into a nested ProcessPoolExecutor. Workers therefore write into a
    Manager-backed queue proxy, and this helper forwards those records into the
    inherited queue used by the API/WebSocket layer.
    """
    while True:
        try:
            record = worker_log_queue.get()
        except Exception:
            break
        if record is None:
            break
        try:
            parent_log_queue.put(record)
        except Exception:
            break


def _serialize_returns(returns) -> dict:
    """Convert a pandas Series (or dict) of returns into a JSON-safe
    {iso_date: float} dict. Used for both SQLite persistence and the
    legacy JSON backup so they stay structurally identical."""
    if returns is None or not hasattr(returns, "items"):
        return {}
    out = {}
    for k, v in returns.items():
        try:
            key = k.isoformat() if hasattr(k, "isoformat") else str(k)
            out[key] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _configured_worker_limit(explicit_value, env_name: str):
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Parallel] Ignoring invalid {env_name}={raw!r}")
        return None
    return value if value > 0 else None


def _configured_timeout(explicit_value, env_name: str, default: float | None = None):
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Parallel] Ignoring invalid {env_name}={raw!r}")
        return default
    return value if value > 0 else None


def _configured_positive_int(explicit_value, env_name: str, default: int) -> int:
    raw = explicit_value if explicit_value is not None else os.getenv(env_name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning(f"[Config] Ignoring invalid {env_name}={raw!r}")
        return default
    if value <= 0:
        logger.warning(f"[Config] Ignoring non-positive {env_name}={raw!r}")
        return default
    return value


def _configured_swarm_executor(explicit_value) -> str:
    raw = explicit_value if explicit_value is not None else os.getenv("AIMINER_SWARM_EXECUTOR")
    value = str(raw or "process").strip().lower()
    aliases = {
        "processes": "process",
        "multiprocess": "process",
        "multi-process": "process",
        "threads": "thread",
        "threaded": "thread",
    }
    value = aliases.get(value, value)
    if value not in {"process", "thread"}:
        logger.warning(
            f"[Parallel] Ignoring invalid AIMINER_SWARM_EXECUTOR={raw!r}; using 'process'."
        )
        return "process"
    return value


def _terminate_process_pool(executor) -> None:
    terminate_workers = getattr(executor, "terminate_workers", None)
    if callable(terminate_workers):
        try:
            terminate_workers()
            return
        except Exception as exc:
            logger.debug(f"[Parallel] terminate_workers failed: {exc}")

    processes = getattr(executor, "_processes", None)
    if not isinstance(processes, dict):
        return
    for process in list(processes.values()):
        terminate = getattr(process, "terminate", None)
        if callable(terminate):
            try:
                terminate()
            except Exception as exc:
                logger.debug(f"[Parallel] process terminate failed: {exc}")


def _is_broken_process_pool_error(exc: BaseException) -> bool:
    if isinstance(exc, BrokenProcessPool):
        return True
    message = str(exc).lower()
    exc_name = type(exc).__name__.lower()
    return (
        "brokenprocesspool" in exc_name
        or "process pool was terminated abruptly" in message
        or "process pool is not usable anymore" in message
    )


def _cancel_pending_futures(futures, completed) -> int:
    pending = set(futures) - set(completed)
    for future in pending:
        try:
            future.cancel()
        except Exception as exc:
            logger.debug(f"[Parallel] future cancel failed: {exc}")
    return len(pending)


def _bounded_worker_count(task_count: int, configured_limit=None) -> int:
    if task_count <= 1:
        return 1
    cpu_limit = os.cpu_count() or 1
    hard_limit = cpu_limit
    if configured_limit is not None:
        hard_limit = min(hard_limit, int(configured_limit))
    return max(1, min(task_count, hard_limit))


def _coerce_returns_series(returns) -> pd.Series:
    if isinstance(returns, pd.Series):
        series = returns.copy(deep=False)
    elif isinstance(returns, dict):
        series = pd.Series(returns, dtype=float)
    elif returns is None:
        return pd.Series(dtype=float)
    else:
        try:
            series = pd.Series(returns, dtype=float)
        except Exception:
            return pd.Series(dtype=float)

    if series.empty:
        return pd.Series(dtype=float)

    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    series = pd.to_numeric(series, errors="coerce")
    valid_mask = series.index.notna() & series.notna()
    if not valid_mask.any():
        return pd.Series(dtype=float)
    return series[valid_mask].sort_index()


def _factor_return_series(factor: dict) -> pd.Series:
    cached = factor.get("_normalized_return_series")
    if isinstance(cached, pd.Series):
        return cached
    series = _coerce_returns_series(
        factor.get("strategy_daily_returns") or factor.get("returns")
    )
    factor["_normalized_return_series"] = series
    return series


def _series_correlation(left: pd.Series, right: pd.Series, min_overlap: int = 10):
    if left is None or right is None or left.empty or right.empty:
        return None

    overlap = left.index.intersection(right.index)
    if len(overlap) < min_overlap:
        return None

    left_aligned = left.reindex(overlap)
    right_aligned = right.reindex(overlap)
    valid_mask = left_aligned.notna() & right_aligned.notna()
    if int(valid_mask.sum()) < min_overlap:
        return None

    corr = left_aligned[valid_mask].corr(right_aligned[valid_mask])
    return float(corr) if pd.notna(corr) else None


def _invert_returns(returns):
    if isinstance(returns, pd.Series):
        return -returns
    if isinstance(returns, dict):
        inverted = {}
        for key, value in returns.items():
            try:
                inverted[key] = -float(value)
            except (TypeError, ValueError):
                continue
        return inverted
    if returns is None:
        return returns
    try:
        return -pd.Series(returns, dtype=float)
    except Exception:
        return returns


def _is_simulated_factor(factor: dict) -> bool:
    metrics = factor.get("metrics") or {}
    return bool(factor.get("is_simulated") or metrics.get("_simulated"))


def _atomic_write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _orient_negative_ic_factor(factor: dict, threshold: float) -> dict:
    perf = float(factor.get("perf_metric", 0.0) or 0.0)
    if perf >= -threshold:
        return factor

    factor["raw_perf_metric"] = perf
    factor["perf_metric"] = abs(perf)
    factor["signal_direction"] = -1
    factor["returns"] = _invert_returns(factor.get("returns"))
    factor.pop("_normalized_return_series", None)

    metrics = dict(factor.get("metrics") or {})
    for key in ("information_coefficient", "ic", "rank_ic"):
        if key in metrics:
            try:
                metrics[f"raw_{key}"] = float(metrics[key])
                metrics[key] = abs(float(metrics[key]))
            except (TypeError, ValueError):
                pass
    if metrics:
        factor["metrics"] = metrics

    selection = factor.get("selection_score")
    try:
        if selection is not None and float(selection) < 0:
            factor["selection_score"] = abs(float(selection))
    except (TypeError, ValueError):
        pass

    return factor


load_dotenv()


# --- Portfolio Manager Core ---


class PortfolioManager:
    # ... (rest of the class)
    def __init__(self, roles=None, **kwargs):
        self.settings = build_settings(kwargs)
        self.roles = roles or [
            "You are an expert in mean-reversion trading, focusing on short-term price overreactions.",
            "You are an expert in momentum and trend-following, using Moving Averages and MACD.",
            "You are a statistical arbitrage expert, looking for cross-sectional market anomalies.",
        ]
        self.researchers = []
        self.alpha_pool = []
        self.strategy_pool = []
        self.kwargs = dict(kwargs)
        self.kwargs.setdefault("llm_provider", self.settings.llm_provider)
        self.kwargs.setdefault("llm_model", self.settings.llm_model)
        self.kwargs.setdefault("llm_base_url", self.settings.llm_base_url)
        self.kwargs.setdefault("llm_reasoning_effort", self.settings.llm_reasoning_effort)
        self.kwargs.setdefault("embedding_provider", self.settings.embedding_provider)
        self.kwargs.setdefault("evaluation_mode", self.settings.evaluation_mode)
        self.kwargs.setdefault("evaluation_engine", self.settings.evaluation_engine)
        self.kwargs.setdefault("data_backend", self.settings.data_backend)
        self.kwargs.setdefault("market_mode", self.settings.market_mode)
        self.kwargs.setdefault("market_profile", self.settings.market_profile)
        self.kwargs.setdefault("market_profiles", self.settings.market_profiles)
        self.kwargs.setdefault("local_data_path", self.settings.local_data_path)
        self.kwargs.setdefault("local_data_layout", self.settings.local_data_layout)
        self.kwargs.setdefault("market_start", self.settings.market_start)
        self.kwargs.setdefault("market_end", self.settings.market_end)
        self.kwargs.setdefault("use_gpu", self.settings.use_gpu)
        self.kwargs.setdefault("rebuild_rag", self.settings.rebuild_rag)
        self.kwargs.setdefault("wiki_bootstrap", self.settings.wiki_bootstrap)
        self.kwargs.setdefault("disable_early_stop", self.settings.disable_early_stop)
        self.run_id = kwargs.get("run_id") or new_run_id()
        self.max_swarm_workers = _configured_worker_limit(
            kwargs.get("max_swarm_workers"),
            "AIMINER_MAX_WORKERS_PER_SWARM",
        )
        self.max_strategy_workers = _configured_worker_limit(
            kwargs.get("max_strategy_workers"),
            "AIMINER_MAX_STRATEGY_WORKERS",
        )
        self.kwargs.pop("swarm_global_timeout_seconds", None)
        self.swarm_global_timeout = _configured_timeout(
            kwargs.pop("swarm_global_timeout_seconds", None),
            "AIMINER_SWARM_GLOBAL_TIMEOUT_SECONDS",
            600.0,
        )
        self.kwargs.pop("swarm_executor", None)
        self.swarm_executor = _configured_swarm_executor(
            kwargs.pop("swarm_executor", None)
        )
        self.kwargs.pop("crossover_iterations", None)
        self.crossover_iterations = _configured_positive_int(
            kwargs.pop("crossover_iterations", None),
            "AIMINER_CROSSOVER_ITERATIONS",
            1,
        )
        self.summary_agent = SummaryAgent(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            reasoning_effort=self.settings.llm_reasoning_effort,
            settings=self.settings,
        )
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for long-term factor tracking.

        Schema carries the full factor detail (metrics/returns/is_effective)
        so the HTTP API never needs to cross-check against the JSON backup.
        """
        self.settings.results_path.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.settings.db_path)
        with sqlite3.connect(self.db_path) as conn:
            # WAL allows concurrent reads during writes (swarm writes while
            # TUI/API reads — no more "database is locked" errors).
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute("""
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
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alpha_timestamp ON alpha_pool(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alpha_run_id ON alpha_pool(run_id)"
            )
            # Idempotent migration for pre-existing databases created before
            # the extended schema landed.
            for col, ddl in [
                ("metrics_json", "ALTER TABLE alpha_pool ADD COLUMN metrics_json TEXT"),
                ("returns_json", "ALTER TABLE alpha_pool ADD COLUMN returns_json TEXT"),
                ("is_effective", "ALTER TABLE alpha_pool ADD COLUMN is_effective INTEGER"),
                ("perf_metric",  "ALTER TABLE alpha_pool ADD COLUMN perf_metric REAL"),
                ("selection_score", "ALTER TABLE alpha_pool ADD COLUMN selection_score REAL"),
                ("best_strategy_id", "ALTER TABLE alpha_pool ADD COLUMN best_strategy_id TEXT"),
                ("best_strategy_metrics_json", "ALTER TABLE alpha_pool ADD COLUMN best_strategy_metrics_json TEXT"),
                ("execution_style", "ALTER TABLE alpha_pool ADD COLUMN execution_style TEXT"),
                ("run_id", "ALTER TABLE alpha_pool ADD COLUMN run_id TEXT"),
                ("agent_id", "ALTER TABLE alpha_pool ADD COLUMN agent_id TEXT"),
                ("iteration", "ALTER TABLE alpha_pool ADD COLUMN iteration INTEGER"),
                ("evaluation_mode", "ALTER TABLE alpha_pool ADD COLUMN evaluation_mode TEXT"),
                ("evaluation_engine", "ALTER TABLE alpha_pool ADD COLUMN evaluation_engine TEXT"),
                ("data_backend", "ALTER TABLE alpha_pool ADD COLUMN data_backend TEXT"),
                ("market_mode", "ALTER TABLE alpha_pool ADD COLUMN market_mode TEXT"),
                ("market_profile", "ALTER TABLE alpha_pool ADD COLUMN market_profile TEXT"),
                ("llm_provider", "ALTER TABLE alpha_pool ADD COLUMN llm_provider TEXT"),
                ("llm_model", "ALTER TABLE alpha_pool ADD COLUMN llm_model TEXT"),
                ("is_simulated", "ALTER TABLE alpha_pool ADD COLUMN is_simulated INTEGER"),
            ]:
                try:
                    cursor.execute(ddl)
                except sqlite3.OperationalError:
                    pass  # column already exists
                    
            # Portfolio table
            cursor.execute("""
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
            """)
            conn.commit()
        ensure_strategy_table(self.db_path)
        ensure_agent_checkpoint_table(self.db_path)
        self._backfill_from_json()

    def _backfill_from_json(self):
        """One-shot backfill: populate extended columns for rows created
        before the schema change, pulling data from the configured alpha_pool.json
        when the id still matches. Rows with no match remain NULL — the
        frontend handles that gracefully."""
        json_path = self.settings.results_path / "alpha_pool.json"
        if not json_path.exists():
            return

        # Fast path: if every row already has metrics_json populated, skip entirely.
        with sqlite3.connect(self.db_path) as conn:
            null_count = conn.execute(
                "SELECT COUNT(*) FROM alpha_pool WHERE metrics_json IS NULL"
            ).fetchone()[0]
        if null_count == 0:
            return

        try:
            with json_path.open("r", encoding="utf-8") as f:
                pool = json.load(f)
        except Exception as e:
            logger.warning(f"[DB Backfill] Failed to read {json_path}: {e}")
            return
        if not isinstance(pool, list) or not pool:
            return

        with sqlite3.connect(self.db_path) as conn:
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
                    continue  # row missing or already backfilled
                metrics_json = json.dumps(entry.get("metrics") or {}, ensure_ascii=False)
                returns_json = json.dumps(entry.get("returns") or {}, ensure_ascii=False)
                is_effective = entry.get("is_effective")
                cursor.execute(
                    """UPDATE alpha_pool
                       SET metrics_json=?, returns_json=?, is_effective=?, perf_metric=?
                       WHERE id=?""",
                    (
                        metrics_json,
                        returns_json,
                        int(is_effective) if isinstance(is_effective, bool) else is_effective,
                        entry.get("perf_metric"),
                        fid,
                    ),
                )
            conn.commit()

    def _write_alpha_pool_json_backup(self):
        """Mirror SQLite alpha_pool into the legacy JSON file atomically.

        SQLite is the source of truth. Keeping the JSON backup as a full DB
        mirror avoids stale current-run-only snapshots being mistaken for the
        complete alpha pool.
        """
        output_path = self.settings.results_path / "alpha_pool.json"
        if not os.path.exists(self.db_path):
            _atomic_write_json(output_path, [])
            return

        records = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM alpha_pool ORDER BY timestamp DESC"
                ).fetchall()
            except sqlite3.OperationalError as exc:
                logger.warning(f"[JSON Backup] Failed to read alpha_pool: {exc}")
                return

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

        _atomic_write_json(output_path, records)

# --- Factor Pool Management ---

    def dispatch_tasks(self, log_queue=None):
        """Prepare kwargs for sub-agents to allow pickling in ProcessPoolExecutor."""
        self.researchers = []
        profiles = (
            self.settings.market_profiles
            if self.settings.market_mode == "batch"
            else [self.settings.market_profile]
        )
        counter = 1
        for profile in profiles:
            for role in self.roles:
                task_kwargs = dict(self.kwargs)
                task_kwargs["role_prompt"] = role
                task_kwargs["run_id"] = self.run_id
                task_kwargs["agent_id"] = new_agent_id(counter)
                task_kwargs["market_profile"] = profile
                task_kwargs["settings"] = self.settings
                if self.settings.market_mode == "batch":
                    task_kwargs["market_profiles"] = [profile]
                    task_kwargs["market_mode"] = "single"
                if log_queue:
                    task_kwargs["log_queue"] = log_queue
                self.researchers.append(task_kwargs)
                counter += 1

    def evaluate_and_combine(self, results_list):
        """Core logic: survival of the fittest and correlation culling."""
        logger.info("=== Manager Evaluation & Synthesis ===")
        valid_factors = []

        # 1. First-pass filter: Absolute performance threshold
        threshold = IC_CULL_THRESHOLD
        for res in results_list:
            if res.get("error"):
                logger.warning(
                    f"[Rejected:error] {res['role'][:30]}... failed with error: {res['error']}"
                )
                continue
            if _is_simulated_factor(res):
                label = str(res.get("role") or res.get("hypothesis") or "?")
                logger.warning(
                    f"[Rejected:simulated] {label[:30]}... used simulated metrics and will not enter Alpha Pool."
                )
                continue

            perf = float(res.get("perf_metric", 0.0) or 0.0)
            if perf > threshold:
                valid_factors.append(res)
            elif perf < -threshold:
                valid_factors.append(_orient_negative_ic_factor(res, threshold))
                label = str(res.get("role") or res.get("hypothesis") or "?")
                logger.info(
                    f"[Accepted:inverse_ic] {label[:30]}... negative IC ({perf:.4f}) will be traded with inverted signal."
                )
            else:
                logger.info(
                    f"[Rejected:threshold] {res['role'][:30]}... generated factor IC ({perf:.4f}) below threshold {threshold}."
                )

        # 2. Second-pass filter: Correlation (multicollinearity) check
        final_pool = []
        for new_factor in valid_factors:
            is_redundant = False
            new_returns = _factor_return_series(new_factor)

            if new_returns.empty:
                logger.warning(
                    f"[Rejected:empty_returns] {new_factor['role'][:30]}... has empty returns series."
                )
                continue

            for existing_factor in final_pool:
                existing_returns = _factor_return_series(existing_factor)
                if existing_returns.empty:
                    continue

                same_market = (
                    new_factor.get("market_profile") == existing_factor.get("market_profile")
                )
                corr = _series_correlation(new_returns, existing_returns)
                if same_market and corr is not None and corr > 0.7:
                    is_redundant = True
                    logger.info(
                        f"[Rejected:correlated] {new_factor['role'][:30]}... highly correlated (Corr: {corr:.2f}) with existing factor."
                    )
                    break

            if not is_redundant:
                # Assign unique ID
                new_factor["id"] = f"alpha_{uuid.uuid4().hex[:8]}"
                final_pool.append(new_factor)
                logger.success(
                    f"[Accepted] {new_factor['role'][:30]}... (IC: {new_factor['perf_metric']:.4f}) added to Alpha Pool."
                )

        self.alpha_pool = sorted(
            final_pool,
            key=lambda item: (
                float(item.get("selection_score", float("-inf")) or float("-inf")),
                float(item.get("perf_metric", 0.0) or 0.0),
            ),
            reverse=True,
        )
        return self.alpha_pool

    def _recover_checkpoint_results(
        self,
        current_results: list[dict],
        *,
        reason: str = "parallel interruption",
    ) -> list[dict]:
        """Recover best per-agent snapshots after an interrupted parallel swarm."""
        try:
            checkpoints = load_agent_checkpoints(self.db_path, self.run_id)
        except Exception as exc:
            logger.warning(f"[Checkpoint] Failed to load agent checkpoints: {exc}")
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

    def _dedupe_alpha_pool_by_returns(self, *, stage: str) -> None:
        if len(self.alpha_pool) < 2:
            return

        ordered = sorted(
            self.alpha_pool,
            key=lambda item: (
                float(item.get("selection_score", float("-inf")) or float("-inf")),
                float(item.get("perf_metric", 0.0) or 0.0),
            ),
            reverse=True,
        )
        final_pool = []
        rejected_ids = set()
        for factor in ordered:
            new_returns = _factor_return_series(factor)
            is_redundant = False
            for existing_factor in final_pool:
                same_market = (
                    factor.get("market_profile") == existing_factor.get("market_profile")
                )
                if not same_market:
                    continue
                corr = _series_correlation(new_returns, _factor_return_series(existing_factor))
                if corr is not None and corr > 0.7:
                    is_redundant = True
                    rejected_ids.add(factor.get("id"))
                    label = str(factor.get("role") or factor.get("id") or "?")
                    logger.info(
                        f"[Rejected:{stage}_correlated] {label[:30]}... "
                        f"highly correlated after {stage} evaluation (Corr: {corr:.2f})."
                    )
                    break
            if not is_redundant:
                final_pool.append(factor)

        if not rejected_ids:
            self.alpha_pool = ordered
            return

        self.alpha_pool = final_pool
        if self.strategy_pool:
            self.strategy_pool = [
                item
                for item in self.strategy_pool
                if item.get("source_factor_id") not in rejected_ids
            ]

    @staticmethod
    def _factor_score(factor: dict, key: str, default: float = 0.0) -> float:
        try:
            return float(factor.get(key, default) or default)
        except (TypeError, ValueError):
            return default

# --- Genetic Crossover ---

    def _select_crossover_parents(self, factors: list[dict] | None = None) -> tuple[dict, dict]:
        pool = list(factors if factors is not None else self.alpha_pool)
        if len(pool) < 2:
            raise ValueError("At least two factors are required for genetic crossover.")
        ranked = sorted(
            pool,
            key=lambda item: self._factor_score(item, "perf_metric"),
            reverse=True,
        )
        return ranked[0], ranked[1]

    def _build_crossover_role(self, top1: dict, top2: dict) -> str:
        return (
            "You are an AI Genetic Crossover Expert. Your task is to combine two high-performing alpha factors into a single, "
            "superior hybrid factor. You excel at extracting orthogonal components and merging them logically.\n"
            "Here are the two parent factors:\n"
            f"Parent 1 (IC: {self._factor_score(top1, 'perf_metric'):.4f}): {top1.get('hypothesis') or 'N/A'}\n"
            f"Code: {top1.get('code') or 'N/A'}\n\n"
            f"Parent 2 (IC: {self._factor_score(top2, 'perf_metric'):.4f}): {top2.get('hypothesis') or 'N/A'}\n"
            f"Code: {top2.get('code') or 'N/A'}\n\n"
            "Extract the best ideas from both and synthesize a new Alpha factor."
        )

    def _run_crossover_agent(
        self,
        top1: dict,
        top2: dict,
        *,
        iterations: int | None = None,
        agent_id: str = "agent_crossover",
    ) -> dict:
        logger.info("Spawning Crossover Agent...")
        crossover_kwargs = dict(self.kwargs)
        crossover_kwargs["role_prompt"] = self._build_crossover_role(top1, top2)
        crossover_kwargs["run_id"] = self.run_id
        crossover_kwargs["agent_id"] = agent_id
        crossover_kwargs["max_iterations"] = iterations or self.crossover_iterations
        return run_agent_task(crossover_kwargs)

    def _accept_crossover_result(
        self,
        crossover_result: dict,
        *,
        comparison_pool: list[dict] | None = None,
        threshold: float = 0.01,
    ) -> tuple[bool, str]:
        if crossover_result.get("error"):
            return False, "errored"
        if _is_simulated_factor(crossover_result):
            return False, "simulated"
        if self._factor_score(crossover_result, "perf_metric") <= threshold:
            return False, "threshold"

        new_returns = _coerce_returns_series(crossover_result.get("returns"))
        if not new_returns.empty:
            for existing_factor in list(comparison_pool or self.alpha_pool):
                existing_returns = _factor_return_series(existing_factor)
                if existing_returns.empty:
                    continue
                corr = _series_correlation(new_returns, existing_returns)
                if corr is not None and corr > 0.7:
                    return False, "correlated"

        crossover_result["id"] = crossover_result.get("id") or f"alpha_{uuid.uuid4().hex[:8]}"
        self.alpha_pool.append(crossover_result)
        return True, "accepted"

    def run_genetic_crossover(
        self,
        *,
        parent_factors: list[dict] | None = None,
        comparison_pool: list[dict] | None = None,
        iterations: int | None = None,
        persist: bool = False,
        threshold: float = 0.01,
        agent_id: str = "agent_crossover",
    ) -> dict:
        top1, top2 = self._select_crossover_parents(parent_factors)
        result = self._run_crossover_agent(
            top1,
            top2,
            iterations=iterations,
            agent_id=agent_id,
        )
        accepted, reason = self._accept_crossover_result(
            result,
            comparison_pool=comparison_pool,
            threshold=threshold,
        )
        if accepted:
            logger.success(
                f"[Crossover Success] Hybrid factor IC: {self._factor_score(result, 'perf_metric'):.4f}"
            )
            if persist:
                self._persist_alpha_factors([result])
        elif reason == "correlated":
            logger.warning(
                "[Crossover Failed] Hybrid factor is highly correlated with existing factors in the same market."
            )
        else:
            logger.warning("[Crossover Failed] Hybrid factor did not meet threshold or errored.")

        return {
            "status": "accepted" if accepted else "rejected",
            "reason": reason,
            "parent_factor_ids": [top1.get("id"), top2.get("id")],
            "factor": result,
        }

    # --- Result Persistence ---

    def _persist_alpha_factors(self, factors: list[dict] | None = None) -> list[dict]:
        factors_to_persist = list(factors if factors is not None else self.alpha_pool)
        if not factors_to_persist:
            return []

        logger.info(f"Generating reports and persisting {len(factors_to_persist)} factors...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for factor in factors_to_persist:
                factor.pop("_normalized_return_series", None)
                if not factor.get("id"):
                    factor["id"] = f"alpha_{uuid.uuid4().hex[:8]}"
                report_path = factor.get("report_path") or self.summary_agent.generate_markdown_report(factor)
                factor["report_path"] = report_path

                metrics = factor.get("metrics") or {}
                returns_dict = _serialize_returns(factor.get("returns"))
                is_effective = factor.get("is_effective")

                try:
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
                            metrics.get("information_coefficient", 0.0),
                            metrics.get("rank_ic", 0.0),
                            report_path,
                            json.dumps(metrics, ensure_ascii=False),
                            json.dumps(returns_dict, ensure_ascii=False),
                            int(is_effective)
                            if isinstance(is_effective, bool)
                            else is_effective,
                            factor.get("perf_metric"),
                            factor.get("selection_score"),
                            factor.get("best_strategy_id"),
                            json.dumps(factor.get("best_strategy_metrics") or {}, ensure_ascii=False),
                            factor.get("execution_style"),
                            factor.get("run_id", self.run_id),
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
                except Exception as db_err:
                    logger.warning(
                        f"[DB] Failed to stage factor '{factor.get('hypothesis', '?')}': {db_err}"
                    )

        self._write_alpha_pool_json_backup()
        logger.success(
            f"Alpha Pool saved to {self.settings.results_path / 'alpha_pool.json'} and SQLite."
        )
        return factors_to_persist

    # --- Swarm Execution ---

    def run_swarm(self, parallel=False, log_queue=None):
        with logger.contextualize(**log_context(run_id=self.run_id)):
            # 1. Extract global RiceQuant Auth
            if self.kwargs.get("data_backend", self.kwargs.get("evaluation_mode", "ricequant")) == "ricequant":
                logger.info("Initializing Global RiceQuant Auth...")
                try:
                    init_rq_auth()
                except Exception as e:
                    logger.error(f"Global RiceQuant Auth failed: {e}")

            # 2. Shared Wiki Initialization (Once per swarm run)
            if self.kwargs.get("wiki_bootstrap"):
                from aiminer.core.hybrid_knowledge import HybridKnowledge

                logger.info(
                    "Main process synthesizing shared knowledge base (LLM Wiki)..."
                )
                knowledge = HybridKnowledge(settings=self.settings)
                knowledge.bootstrap_wiki(force=False)

            worker_log_manager = None
            worker_log_queue = None
            worker_log_thread = None
            dispatch_log_queue = log_queue
            if parallel and self.swarm_executor == "process" and log_queue is not None:
                worker_log_manager = multiprocessing.Manager()
                worker_log_queue = worker_log_manager.Queue()
                worker_log_thread = threading.Thread(
                    target=_forward_worker_logs,
                    args=(worker_log_queue, log_queue),
                    daemon=True,
                )
                worker_log_thread.start()
                dispatch_log_queue = worker_log_queue

            task_log_queue = (
                None
                if parallel and self.swarm_executor == "process"
                else dispatch_log_queue
            )
            self.dispatch_tasks(log_queue=task_log_queue)

            all_results = []
            try:
                if parallel:
                    max_workers = _bounded_worker_count(
                        len(self.researchers),
                        self.max_swarm_workers,
                    )
                    if self.swarm_executor == "thread":
                        logger.info(
                            "Running sub-agents in PARALLEL mode (ThreadPool)..."
                        )
                        executor = concurrent.futures.ThreadPoolExecutor(
                            max_workers=max_workers
                        )
                        timed_out = False
                        futures = {}
                        completed = set()
                        try:
                            futures = {
                                executor.submit(run_agent_task, kwargs): kwargs
                                for kwargs in self.researchers
                            }
                            for future in concurrent.futures.as_completed(
                                futures,
                                timeout=self.swarm_global_timeout,
                            ):
                                completed.add(future)
                                try:
                                    result = future.result()
                                    all_results.append(result)
                                except Exception as exc:
                                    logger.error(f"Agent generated an exception: {exc}")
                        except concurrent.futures.TimeoutError:
                            timed_out = True
                            pending_count = _cancel_pending_futures(futures, completed)
                            logger.error(
                                f"Parallel agent swarm exceeded global timeout "
                                f"{self.swarm_global_timeout}s; cancelled {pending_count} pending agent(s)."
                            )
                            all_results = self._recover_checkpoint_results(
                                all_results,
                                reason="parallel timeout",
                            )
                        finally:
                            try:
                                executor.shutdown(
                                    wait=not timed_out,
                                    cancel_futures=timed_out,
                                )
                            except TypeError:
                                executor.shutdown(wait=not timed_out)
                    else:
                        logger.info(
                            "Running sub-agents in PARALLEL mode (Multi-Process)..."
                        )
                        try:
                            executor = concurrent.futures.ProcessPoolExecutor(
                                max_workers=max_workers,
                                initializer=_init_worker_context,
                                initargs=(dispatch_log_queue,),
                            )
                            timed_out = False
                            pool_broken = False
                            futures = {}
                            completed = set()
                            try:
                                futures = {
                                    executor.submit(run_agent_task, kwargs): kwargs
                                    for kwargs in self.researchers
                                }
                                for future in concurrent.futures.as_completed(
                                    futures,
                                    timeout=self.swarm_global_timeout,
                                ):
                                    completed.add(future)
                                    try:
                                        result = future.result()
                                        all_results.append(result)
                                    except Exception as exc:
                                        if _is_broken_process_pool_error(exc):
                                            pool_broken = True
                                            role = str(
                                                futures.get(future, {}).get(
                                                    "role_prompt", "unknown"
                                                )
                                            )
                                            pending_count = _cancel_pending_futures(
                                                futures,
                                                completed,
                                            )
                                            _terminate_process_pool(executor)
                                            logger.error(
                                                "[Parallel] Process pool broke while "
                                                f"collecting role {role[:40]!r}: {exc}; "
                                                f"cancelled {pending_count} pending agent(s)."
                                            )
                                            all_results = self._recover_checkpoint_results(
                                                all_results,
                                                reason="parallel worker failure",
                                            )
                                            break
                                        logger.error(
                                            f"Agent generated an exception: {exc}"
                                        )
                            except concurrent.futures.TimeoutError:
                                timed_out = True
                                pending_count = _cancel_pending_futures(
                                    futures, completed
                                )
                                _terminate_process_pool(executor)
                                logger.error(
                                    f"Parallel agent swarm exceeded global timeout "
                                    f"{self.swarm_global_timeout}s; cancelled {pending_count} pending agent(s)."
                                )
                                all_results = self._recover_checkpoint_results(
                                    all_results,
                                    reason="parallel timeout",
                                )
                            except Exception as exc:
                                if not _is_broken_process_pool_error(exc):
                                    raise
                                pool_broken = True
                                pending_count = _cancel_pending_futures(
                                    futures, completed
                                )
                                _terminate_process_pool(executor)
                                logger.error(
                                    "[Parallel] Process pool broke while waiting for "
                                    f"agent futures: {exc}; cancelled {pending_count} pending agent(s)."
                                )
                                all_results = self._recover_checkpoint_results(
                                    all_results,
                                    reason="parallel worker failure",
                                )
                            finally:
                                shutdown = getattr(executor, "shutdown", None)
                                if shutdown is not None:
                                    cancel_futures = timed_out or pool_broken
                                    try:
                                        shutdown(
                                            wait=not cancel_futures,
                                            cancel_futures=cancel_futures,
                                        )
                                    except TypeError:
                                        shutdown(wait=not cancel_futures)
                        except KeyboardInterrupt:
                            logger.warning(
                                "KeyboardInterrupt received – shutting down sub-agents gracefully"
                            )
                            raise
                else:
                    logger.info("Running sub-agents in SERIAL mode...")
                    for kwargs in self.researchers:
                        result = run_agent_task(kwargs)
                        all_results.append(result)
            finally:
                if worker_log_queue is not None:
                    try:
                        worker_log_queue.put(None)
                    except Exception:
                        pass
                if worker_log_thread is not None:
                    worker_log_thread.join(timeout=2)
                if worker_log_manager is not None:
                    worker_log_manager.shutdown()

            # Manager evaluates all
            all_results = self._recover_checkpoint_results(all_results)
            self.evaluate_and_combine(all_results)
            self.evaluate_strategies()

            # --- Genetic Algorithm Crossover ---
            if len(self.alpha_pool) >= 2:
                logger.info("=== Manager Genetic Crossover ===")
                self.run_genetic_crossover()
            # -----------------------------------

            # 3. Final Step: Generate Reports and Persistent Storage
            if self.alpha_pool:
                self._persist_alpha_factors()

            if self.strategy_pool:
                logger.info(
                    f"Persisting {len(self.strategy_pool)} strategy backtests..."
                )
                for payload in self.strategy_pool:
                    try:
                        persist_strategy_result(self.db_path, payload)
                    except Exception as exc:
                        logger.warning(
                            f"[Strategy DB] Failed to persist strategy '{payload.get('strategy_id', '?')}': {exc}"
                        )

            # --- Portfolio Construction ---
            if len(self.alpha_pool) >= 2:
                logger.info("=== Synthesizing Factor Portfolio ===")
                try:
                    portfolio_agent = PortfolioAgent(
                        provider=self.kwargs.get("llm_provider"),
                        model=self.kwargs.get("llm_model"),
                        base_url=self.kwargs.get("llm_base_url"),
                        reasoning_effort=self.kwargs.get("llm_reasoning_effort"),
                    )
                    returns_dict = {}
                    factors_for_portfolio = []
                    for factor in self.alpha_pool:
                        fid = factor.get("id")
                        ret = _factor_return_series(factor)
                        if fid and not ret.empty:
                            returns_dict[fid] = ret
                            factors_for_portfolio.append(factor)
                            
                    if len(returns_dict) >= 2:
                        returns_df = pd.DataFrame(returns_dict)
                        # Ensure numeric index for correlation if needed, or date parsing
                        decision = portfolio_agent.select_method(factors_for_portfolio, returns_df)
                        portfolio_result = construct_portfolio(returns_dict, method=decision.method)
                        logger.success(f"Portfolio constructed using {decision.method} | Diversification Ratio: {portfolio_result['diversification_ratio']:.4f}")
                        
                        # Persist to database
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            pid = f"portfolio_{uuid.uuid4().hex[:8]}"
                            cursor.execute("""
                                INSERT INTO portfolio_pool (id, run_id, method, rationale, weights_json, returns_json, diversification_ratio)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                pid,
                                self.run_id,
                                decision.method,
                                decision.rationale,
                                json.dumps(portfolio_result["weights"], ensure_ascii=False),
                                json.dumps(_serialize_returns(portfolio_result["portfolio_returns"]), ensure_ascii=False),
                                float(portfolio_result["diversification_ratio"])
                            ))
                            conn.commit()
                except Exception as e:
                    logger.error(f"Portfolio construction failed: {e}")
            # ------------------------------

            logger.info(
                f"Swarm execution completed. {len(self.alpha_pool)} orthogonal factors found; {len(self.strategy_pool)} strategies evaluated."
            )
            return self.alpha_pool

    # --- Strategy Evaluation ---

    def evaluate_strategies(self):
        if not self.alpha_pool:
            self.strategy_pool = []
            return []

        try:
            from aiminer.core.manual_runner import run_manual_strategy_backtest, strategy_id_for
        except Exception as exc:
            logger.warning(f"[Strategy Eval] Unable to import strategy runner: {exc}")
            self.strategy_pool = []
            return []

        def _fallback_candidates(factor):
            market_profile = factor.get("market_profile", self.settings.market_profile)
            execution_style = str(factor.get("execution_style") or "")
            if market_profile == "futures":
                template_name = "ts_long_flat" if execution_style == "ts_trend" else "ts_long_short"
            else:
                template_name = "ts_long_flat" if execution_style == "ts_trend" else "cs_top_bottom"
            cfg = strategy_templates()[template_name].model_copy(
                update={
                    "label": f"{template_name}:{factor.get('hypothesis') or factor.get('id')}",
                    "start_date": self.settings.market_start or "2017-01-01",
                    "end_date": self.settings.market_end or "2020-10-31",
                    "engine": self.settings.evaluation_engine,
                    "market": factor.get("market_profile", self.settings.market_profile),
                }
            )
            return [
                {
                    "template_name": template_name,
                    "rationale": (
                        f"Manager fallback template {template_name} selected for "
                        f"market_profile={market_profile}, execution_style={execution_style or 'default'}."
                    ),
                    "strategy_config": cfg.model_dump(mode="json"),
                }
            ]

        def _score_result(factor, result):
            metrics = result.get("metrics") or {}
            if metrics:
                try:
                    return float(
                        selection_score(
                            metrics,
                            factor_ic=float(factor.get("perf_metric", 0.0) or 0.0),
                            walk_forward=(result.get("walk_forward") or {}).get("aggregate"),
                        )
                    )
                except Exception as exc:
                    logger.debug(
                        f"[Strategy Eval] Failed to recompute score for "
                        f"{result.get('strategy_id', '?')}: {exc}"
                    )
            return float(
                result.get(
                    "selection_score",
                    factor.get("selection_score", factor.get("perf_metric", 0.0)),
                )
                or 0.0
            )

        def _normalize_result(factor, result, idx):
            payload = dict(result)
            payload.setdefault("run_type", "strategy_backtest")
            payload.setdefault("status", "ok")
            payload.setdefault("chart_paths", {})
            payload.setdefault("ran_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
            payload.setdefault("label", (payload.get("strategy_config") or {}).get("label"))
            payload.setdefault("market", (payload.get("strategy_config") or {}).get("market"))
            payload.setdefault("engine", (payload.get("strategy_config") or {}).get("engine"))
            payload["run_id"] = self.run_id
            payload["source_factor_id"] = factor.get("id")
            payload["agent_id"] = factor.get("agent_id")
            payload["candidate_rank"] = int(payload.get("candidate_rank", idx) or idx)
            raw_strategy_id = payload.get("raw_strategy_id") or payload.get("strategy_id")
            cache_key = (
                payload.get("cache_key")
                or payload.get("strategy_cache_key")
                or raw_strategy_id
                or f"{factor.get('id') or factor.get('agent_id') or 'factor'}:{idx}"
            )
            payload["cache_key"] = cache_key
            payload["raw_strategy_id"] = raw_strategy_id
            payload["strategy_id"] = strategy_id_for(
                str(cache_key),
                run_id=self.run_id,
                source_factor_id=factor.get("id"),
                agent_id=factor.get("agent_id"),
                candidate_rank=payload["candidate_rank"],
                template_name=payload.get("template_name"),
            )
            payload["is_primary"] = False
            payload["selection_score"] = _score_result(factor, payload)
            payload["market_profile"] = factor.get("market_profile", self.settings.market_profile)
            payload["data_backend"] = factor.get("data_backend", self.settings.data_backend)
            return payload

        def _evaluate_candidate(factor, idx, candidate):
            expression = factor.get("code")
            cfg = candidate.get("strategy_config")
            if not expression or not cfg:
                return None
            try:
                result = run_manual_strategy_backtest(
                    expression,
                    cfg,
                    data_backend=factor.get("data_backend", self.settings.data_backend),
                    market_profile=factor.get("market_profile", self.settings.market_profile),
                    market_mode=factor.get("market_mode", "single"),
                    market_profiles=[factor.get("market_profile", self.settings.market_profile)],
                    local_data_path=self.settings.local_data_path,
                    local_data_layout=self.settings.local_data_layout,
                    run_id=self.run_id,
                    source_factor_id=factor.get("id"),
                    agent_id=factor.get("agent_id"),
                    candidate_rank=idx,
                    template_name=candidate.get("template_name"),
                    rationale=candidate.get("rationale"),
                    signal_multiplier=float(factor.get("signal_direction", 1.0) or 1.0),
                )
            except Exception as exc:
                logger.warning(
                    f"[Strategy Eval] Candidate {candidate.get('template_name', idx)} failed "
                    f"for factor '{factor.get('hypothesis', '?')}': {exc}"
                )
                return None
            payload = dict(result)
            payload.setdefault("template_name", candidate.get("template_name"))
            payload.setdefault("rationale", candidate.get("rationale"))
            return _normalize_result(factor, payload, idx)

        strategy_results = []
        normalized_by_factor = {}
        pending_evaluations = []
        for factor_idx, factor in enumerate(self.alpha_pool):
            existing_results = [
                dict(item) for item in (factor.get("strategy_results") or []) if isinstance(item, dict)
            ]
            best_existing = factor.get("best_strategy_result") or {}
            if best_existing and isinstance(best_existing, dict):
                best_id = best_existing.get("strategy_id")
                if best_id and not any(item.get("strategy_id") == best_id for item in existing_results):
                    existing_results.insert(0, dict(best_existing))
            if existing_results:
                normalized_by_factor[factor_idx] = [
                    _normalize_result(factor, result, idx)
                    for idx, result in enumerate(existing_results, start=1)
                ]
            else:
                candidates = [
                    dict(item)
                    for item in (factor.get("strategy_candidates") or [])
                    if isinstance(item, dict)
                ]
                for idx, candidate in enumerate(candidates or _fallback_candidates(factor), start=1):
                    pending_evaluations.append((factor_idx, factor, idx, candidate))

        strategy_worker_count = _bounded_worker_count(
            len(pending_evaluations),
            self.max_strategy_workers,
        )
        if pending_evaluations:
            if strategy_worker_count > 1:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=strategy_worker_count
                ) as executor:
                    futures = {
                        executor.submit(_evaluate_candidate, factor, idx, candidate): (
                            factor_idx,
                            idx,
                        )
                        for factor_idx, factor, idx, candidate in pending_evaluations
                    }
                    for future in concurrent.futures.as_completed(futures):
                        factor_idx, _ = futures[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            logger.warning(
                                f"[Strategy Eval] Candidate future failed for factor #{factor_idx}: {exc}"
                            )
                            continue
                        if result:
                            normalized_by_factor.setdefault(factor_idx, []).append(result)
            else:
                for factor_idx, factor, idx, candidate in pending_evaluations:
                    result = _evaluate_candidate(factor, idx, candidate)
                    if result:
                        normalized_by_factor.setdefault(factor_idx, []).append(result)

        for factor_idx, factor in enumerate(self.alpha_pool):
            normalized_results = sorted(
                normalized_by_factor.get(factor_idx, []),
                key=lambda item: int(item.get("candidate_rank", 0) or 0),
            )
            if not normalized_results:
                factor["strategy_failure_reason"] = factor.get("strategy_failure_reason") or "no_strategy_results"
                continue

            best = max(
                normalized_results,
                key=lambda item: float(item.get("selection_score", float("-inf")) or float("-inf")),
            )
            best_id = best.get("strategy_id")
            for result in normalized_results:
                result["is_primary"] = bool(best_id and result.get("strategy_id") == best_id)
            factor["strategy_results"] = normalized_results
            factor["best_strategy_result"] = best
            factor["best_strategy_config"] = best.get("strategy_config", {})
            factor["best_strategy_metrics"] = best.get("metrics", {})
            factor["best_strategy_id"] = best_id
            factor["strategy_daily_returns"] = best.get("daily_returns", {})
            factor["_normalized_return_series"] = _coerce_returns_series(
                factor["strategy_daily_returns"]
            )
            factor["selection_score"] = float(
                best.get("selection_score", factor.get("perf_metric", 0.0)) or 0.0
            )
            factor.pop("strategy_failure_reason", None)
            strategy_results.extend(normalized_results)

        self.alpha_pool = sorted(
            self.alpha_pool,
            key=lambda item: (
                float(item.get("selection_score", float("-inf")) or float("-inf")),
                float(item.get("perf_metric", 0.0) or 0.0),
            ),
            reverse=True,
        )
        self.strategy_pool = sorted(
            strategy_results,
            key=lambda item: float(item.get("selection_score", float("-inf")) or float("-inf")),
            reverse=True,
        )
        self._dedupe_alpha_pool_by_returns(stage="strategy")
        return self.strategy_pool


# --- CLI Entry Point ---

def main(args=None):
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    parser = argparse.ArgumentParser(
        description="Multi-Agent AI Alpha Miner - Swarm Manager"
    )
    parser.add_argument(
        "--iterations", type=int, default=2, help="Iterations per sub-agent"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["qlib", "ricequant"],
        default="ricequant",
        help="Evaluation mode",
    )
    parser.add_argument(
        "--data-backend",
        type=str,
        choices=["qlib", "ricequant", "local"],
        help="Data backend",
    )
    parser.add_argument(
        "--engine",
        type=str,
        choices=["pandas", "polars"],
        default="pandas",
        help="Evaluation engine (for ricequant mode)",
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Run sub-agents in parallel"
    )
    parser.add_argument(
        "--wiki-bootstrap",
        action="store_true",
        help="Initialize the LLM Wiki from RAG documents on startup",
    )
    parser.add_argument(
        "--roles", type=str, nargs="+", help="Specific roles to assign to sub-agents"
    )
    parser.add_argument("--run-id", type=str, help="Stable run id for checkpoint resume")
    parser.add_argument("--llm-provider", type=str, help="LLM provider")
    parser.add_argument("--llm-model", type=str, help="Specific LLM model name")
    parser.add_argument("--llm-base-url", type=str, help="Override OpenAI-compatible base URL")
    parser.add_argument(
        "--llm-reasoning-effort",
        type=str,
        choices=["low", "medium", "high", "xhigh"],
        help="Codex reasoning effort",
    )
    parser.add_argument(
        "--embedding-provider", type=str, help="Embedding provider for RAG"
    )
    parser.add_argument(
        "--market-mode",
        type=str,
        choices=["single", "batch", "mixed"],
        default="single",
        help="Market execution mode",
    )
    parser.add_argument(
        "--market-profile",
        type=str,
        choices=["cn_stock", "us_stock", "futures"],
        default=None,
        help="Market profile for this run (auto-detects futures for bundled local futures data)",
    )
    parser.add_argument(
        "--market-profiles",
        type=str,
        help="Comma-separated market profiles for batch/mixed mode",
    )
    parser.add_argument("--local-data-path", type=str, help="Local CSV/Parquet dataset path")
    parser.add_argument(
        "--local-data-layout",
        type=str,
        choices=["auto", "panel", "instrument_files"],
        default="auto",
        help="Local data layout",
    )
    parser.add_argument(
        "--market-start", type=str, help="Market analysis start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--market-end", type=str, help="Market analysis end date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--use-gpu", action="store_true", help="Use GPU for local RAG embedding"
    )
    parser.add_argument("--rebuild-rag", action="store_true", help="Force rebuild RAG")
    parser.add_argument(
        "--swarm-global-timeout-seconds",
        type=float,
        default=None,
        help="Global timeout (seconds) for the entire parallel swarm (default: 600). "
        "Set higher for slow LLMs or many iterations. "
        "Also settable via AIMINER_SWARM_GLOBAL_TIMEOUT_SECONDS env var.",
    )
    parser.add_argument(
        "--swarm-executor",
        type=str,
        choices=["process", "thread"],
        default=None,
        help=(
            "Parallel executor backend for --parallel (default: process). "
            "Use thread when native libraries are unsafe across processes. "
            "Also settable via AIMINER_SWARM_EXECUTOR."
        ),
    )
    parser.add_argument(
        "--crossover-iterations",
        type=int,
        default=None,
        help="Iterations for the final genetic crossover agent (default: 1). "
        "Also settable via AIMINER_CROSSOVER_ITERATIONS env var.",
    )
    parser.add_argument(
        "--disable-early-stop",
        action="store_true",
        help=(
            "Continue until --iterations even when high IC or patience early-stop "
            "criteria are met. Also settable via AIMINER_DISABLE_EARLY_STOP=1."
        ),
    )
    parser.add_argument(
        "--reset",
        action="append",
        choices=("pool", "memory", "rag", "runs", "all"),
        help=(
            "Wipe mining artifacts before starting the swarm. Repeatable. "
            "Always runs as a confirmed move into results/.trash/<ts>/. "
            "Run scripts/reset_workspace.py for dry-run inspection."
        ),
    )
    args = parser.parse_args(args)

    if args.reset:
        from scripts.reset_workspace import build_plan, execute_plan, render_plan, render_result

        plan = build_plan(args.reset)
        logger.info(render_plan(plan))
        summary = execute_plan(plan, confirm=True)
        logger.info("")
        logger.info(render_result(summary))
        logger.info("")

    manager = PortfolioManager(
        roles=args.roles,
        run_id=args.run_id,
        max_iterations=args.iterations,
        evaluation_mode=args.mode,
        data_backend=args.data_backend,
        evaluation_engine=args.engine,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        llm_reasoning_effort=args.llm_reasoning_effort,
        embedding_provider=args.embedding_provider,
        market_mode=args.market_mode,
        market_profile=args.market_profile,
        market_profiles=args.market_profiles,
        local_data_path=args.local_data_path,
        local_data_layout=args.local_data_layout,
        market_start=args.market_start,
        market_end=args.market_end,
        use_gpu=args.use_gpu,
        rebuild_rag=args.rebuild_rag,
        wiki_bootstrap=args.wiki_bootstrap,
        disable_early_stop=args.disable_early_stop,
        swarm_global_timeout_seconds=args.swarm_global_timeout_seconds,
        swarm_executor=args.swarm_executor,
        crossover_iterations=args.crossover_iterations,
    )
    manager.run_swarm(parallel=args.parallel)


if __name__ == "__main__":
    main()
