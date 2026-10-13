# --- Imports & Logging Setup ---

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import argparse
import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import json
import multiprocessing
import random
import sqlite3
import threading
import time
from typing import Any
import uuid

from dotenv import load_dotenv
from loguru import logger
import numpy as np
import pandas as pd
import scipy.stats

from aiminer.core.agent_checkpoint import (
    ensure_agent_checkpoint_table,
    load_agent_checkpoints,
)
from aiminer.core.constants import IC_CULL_THRESHOLD

try:
    from aiminer.core.orthogonalization import (
        compute_cross_sectional_factor_correlation,
        compute_incremental_ic,
    )
except ImportError:
    compute_cross_sectional_factor_correlation = None
    compute_incremental_ic = None
from aiminer.core.runtime import log_context, new_agent_id, new_run_id
from aiminer.core.settings import build_settings
from aiminer.core.strategy import (
    ensure_strategy_table,
    persist_strategy_result,
    selection_score,
    strategy_templates,
)
from aiminer.core.task_state import (
    CancellationToken,
    HeartbeatMonitor,
    SwarmRunExecutionTracker,
)

# Optional deps: keep names on the module so tests can monkeypatch them.
try:
    from aiminer.sub_agent import AlphaResearcher
except ImportError:  # pragma: no cover
    AlphaResearcher = None  # type: ignore[misc, assignment]
try:
    from aiminer.agents.summary_agent import SummaryAgent
except ImportError:  # pragma: no cover
    SummaryAgent = None  # type: ignore[misc, assignment]
try:
    from aiminer.agents.portfolio_agent import PortfolioAgent
except ImportError:  # pragma: no cover
    PortfolioAgent = None  # type: ignore[misc, assignment]
try:
    from aiminer.core.portfolio import construct_portfolio
except ImportError:  # pragma: no cover
    construct_portfolio = None  # type: ignore[misc, assignment]
try:
    from aiminer.core.alphaeval.rq_eval import init_rq_auth
except ImportError:  # pragma: no cover
    init_rq_auth = None  # type: ignore[misc, assignment]


from aiminer.crossover import (
    CROSSOVER_ROLE,
    accept_crossover_result,
    build_crossover_role,
    run_crossover_agent,
    select_crossover_parents,
)
from aiminer.persistence import (
    _atomic_write_json,
    _serialize_returns,
    backfill_alpha_pool_from_json,
    init_portfolio_db,
    persist_alpha_factors,
    recover_checkpoint_results,
    write_alpha_pool_json_backup,
)
from aiminer.scheduler import (
    _WORKER_LOG_QUEUE,
    _bounded_worker_count,
    _cancel_pending_futures,
    _configured_positive_int,
    _configured_swarm_executor,
    _configured_timeout,
    _configured_worker_limit,
    _forward_worker_logs,
    _init_worker_context,
    _is_broken_process_pool_error,
    _is_local_embedding_mode,
    _normalize_role,
    _process_safe_worker_count,
    _terminate_process_pool,
    run_agent_task,
)
from aiminer.selector import (
    _coerce_returns_series,
    _factor_return_series,
    _invert_returns,
    _is_simulated_factor,
    _orient_negative_ic_factor,
    _series_correlation,
    cull_alpha_pool,
    dedupe_alpha_pool_by_returns,
    factor_score,
)

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
        self.n_trials = 0
        self.trial_sharpes: list[float] = []
        self.kwargs = dict(kwargs)
        self.kwargs.setdefault("llm_provider", self.settings.llm_provider)
        self.kwargs.setdefault("llm_model", self.settings.llm_model)
        self.kwargs.setdefault("llm_base_url", self.settings.llm_base_url)
        self.kwargs.setdefault(
            "llm_reasoning_effort", self.settings.llm_reasoning_effort
        )
        self.kwargs.setdefault(
            "embedding_provider", self.settings.embedding_provider
        )
        self.kwargs.setdefault("evaluation_mode", self.settings.evaluation_mode)
        self.kwargs.setdefault(
            "evaluation_engine", self.settings.evaluation_engine
        )
        self.kwargs.setdefault("data_backend", self.settings.data_backend)
        self.kwargs.setdefault("market_mode", self.settings.market_mode)
        self.kwargs.setdefault("market_profile", self.settings.market_profile)
        self.kwargs.setdefault("market_profiles", self.settings.market_profiles)
        self.kwargs.setdefault("local_data_path", self.settings.local_data_path)
        self.kwargs.setdefault(
            "local_data_layout", self.settings.local_data_layout
        )
        self.kwargs.setdefault("market_start", self.settings.market_start)
        self.kwargs.setdefault("market_end", self.settings.market_end)
        self.kwargs.setdefault("use_gpu", self.settings.use_gpu)
        self.kwargs.setdefault("rebuild_rag", self.settings.rebuild_rag)
        self.kwargs.setdefault("wiki_bootstrap", self.settings.wiki_bootstrap)
        self.kwargs.setdefault(
            "disable_early_stop", self.settings.disable_early_stop
        )
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
        self.idempotency_key = kwargs.pop("idempotency_key", None)
        self.cancellation_token = (
            kwargs.pop("cancellation_token", None) or CancellationToken()
        )
        self.execution_tracker = kwargs.pop(
            "execution_tracker", None
        ) or SwarmRunExecutionTracker(self.settings.db_path)
        self.kwargs.pop("idempotency_key", None)
        self.kwargs.pop("cancellation_token", None)
        self.kwargs.pop("execution_tracker", None)

    def _init_db(self):
        """Initialize SQLite database for long-term factor tracking.

        Schema carries the full factor detail (metrics/returns/is_effective)
        so the HTTP API never needs to cross-check against the JSON backup.
        """
        self.settings.results_path.mkdir(parents=True, exist_ok=True)
        self.db_path = str(self.settings.db_path)
        init_portfolio_db(self.db_path, self.settings.results_path)
        self._backfill_from_json()

    def _backfill_from_json(self):
        """One-shot backfill: populate extended columns from JSON backup."""
        json_path = self.settings.results_path / "alpha_pool.json"
        backfill_alpha_pool_from_json(self.db_path, json_path)

    def _write_alpha_pool_json_backup(self):
        """Mirror SQLite alpha_pool into the legacy JSON file atomically."""
        if not os.path.exists(self.db_path):
            _atomic_write_json(
                self.settings.results_path / "alpha_pool.json", []
            )
            return
        write_alpha_pool_json_backup(self.db_path, self.settings.results_path)

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

    def record_trial(self, sharpe_or_factor: float | dict[str, Any]) -> None:
        """Record an evaluated trial for multiple testing tracking."""
        self.n_trials += 1
        if isinstance(sharpe_or_factor, (int, float)):
            self.trial_sharpes.append(float(sharpe_or_factor))
        elif isinstance(sharpe_or_factor, dict):
            sr = sharpe_or_factor.get("metrics", {}).get("sharpe")
            if sr is None:
                sr = sharpe_or_factor.get("perf_metric")
            if sr is not None:
                try:
                    self.trial_sharpes.append(float(sr))
                except (ValueError, TypeError):
                    pass

    def evaluate_and_combine(self, results_list):
        """Drop weak / correlated factors before they enter the pool."""
        for item in results_list:
            if isinstance(item, dict):
                self.n_trials += int(item.get("iteration") or 1)
                sr = item.get("metrics", {}).get("sharpe")
                if sr is None:
                    sr = item.get("perf_metric")
                if sr is not None:
                    try:
                        self.trial_sharpes.append(float(sr))
                    except (ValueError, TypeError):
                        pass
                if item.get("role"):
                    item["role"] = _normalize_role(item.get("role"))
        logger.info("=== Manager Evaluation & Synthesis ===")
        valid_factors = []

        # Keep factors whose |IC| clears the cull threshold.
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

            # P1.1: If validation segment IC is available in holdout_metrics,
            # use validation IC for admission check to prevent train overfitting.
            # Otherwise fall back to perf_metric (train IC or full IC).
            holdout = res.get("holdout_metrics") or {}
            val_ic = holdout.get("val_ic")
            check_metric = (
                val_ic
                if val_ic is not None
                else float(res.get("perf_metric", 0.0) or 0.0)
            )
            perf = float(res.get("perf_metric", 0.0) or 0.0)

            if check_metric > threshold:
                valid_factors.append(res)
            elif check_metric < -threshold:
                valid_factors.append(_orient_negative_ic_factor(res, threshold))
                label = str(res.get("role") or res.get("hypothesis") or "?")
                logger.info(
                    f"[Accepted:inverse_ic] {label[:30]}... negative metric ({check_metric:.4f}) will be traded with inverted signal."
                )
            else:
                logger.info(
                    f"[Rejected:threshold] {res['role'][:30]}... factor metric ({check_metric:.4f}, val_ic={val_ic}) below threshold {threshold}."
                )

        # Drop factors too correlated with ones already in the pool.
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

                same_market = new_factor.get(
                    "market_profile"
                ) == existing_factor.get("market_profile")
                if not same_market:
                    continue

                corr = _series_correlation(new_returns, existing_returns)
                if corr is not None and corr > 0.7:
                    is_redundant = True
                    logger.info(
                        f"[Rejected:correlated_returns] {new_factor['role'][:30]}... highly correlated returns (Corr: {corr:.2f}) with existing factor."
                    )
                    break

                # Cross-sectional factor value correlation check (if available)
                new_fvals = new_factor.get("factor_series")
                exist_fvals = existing_factor.get("factor_series")
                if isinstance(new_fvals, pd.Series) and isinstance(
                    exist_fvals, pd.Series
                ):
                    f_corr = compute_cross_sectional_factor_correlation(
                        new_fvals, exist_fvals
                    )
                    if f_corr is not None and f_corr > 0.75:
                        is_redundant = True
                        logger.info(
                            f"[Rejected:correlated_factor_vals] {new_factor['role'][:30]}... highly correlated factor values (RankCorr: {f_corr:.2f}) with existing factor."
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
                float(
                    item.get("selection_score", float("-inf")) or float("-inf")
                ),
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
        return recover_checkpoint_results(
            self.db_path, self.run_id, current_results, reason=reason
        )

    def _dedupe_alpha_pool_by_returns(self, *, stage: str) -> None:
        if len(self.alpha_pool) < 2:
            return

        ordered = sorted(
            self.alpha_pool,
            key=lambda item: (
                float(
                    item.get("selection_score", float("-inf")) or float("-inf")
                ),
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
                same_market = factor.get(
                    "market_profile"
                ) == existing_factor.get("market_profile")
                if not same_market:
                    continue
                corr = _series_correlation(
                    new_returns, _factor_return_series(existing_factor)
                )
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

    def _select_crossover_parents(
        self, factors: list[dict] | None = None
    ) -> tuple[dict, dict]:
        pool = list(factors if factors is not None else self.alpha_pool)
        return select_crossover_parents(pool, score_fn=self._factor_score)

    def _build_crossover_role(self, top1: dict, top2: dict) -> str:
        return build_crossover_role(top1, top2, score_fn=self._factor_score)

    def _run_crossover_agent(
        self,
        top1: dict,
        top2: dict,
        *,
        iterations: int | None = None,
        agent_id: str = "agent_crossover",
    ) -> dict:
        return run_crossover_agent(
            top1,
            top2,
            run_id=self.run_id,
            kwargs=self.kwargs,
            iterations=iterations or self.crossover_iterations,
            agent_id=agent_id,
            score_fn=self._factor_score,
            run_task_fn=run_agent_task,
        )

    def _accept_crossover_result(
        self,
        crossover_result: dict,
        *,
        comparison_pool: list[dict] | None = None,
        threshold: float = 0.01,
    ) -> tuple[bool, str]:
        accepted, reason = accept_crossover_result(
            crossover_result,
            comparison_pool=(
                comparison_pool
                if comparison_pool is not None
                else self.alpha_pool
            ),
            threshold=threshold,
            score_fn=self._factor_score,
        )
        if accepted:
            self.alpha_pool.append(crossover_result)
        return accepted, reason

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
        if isinstance(result, dict):
            self.n_trials += int(result.get("iteration") or 1)
            sr = result.get("metrics", {}).get("sharpe")
            if sr is None:
                sr = result.get("perf_metric")
            if sr is not None:
                try:
                    self.trial_sharpes.append(float(sr))
                except (ValueError, TypeError):
                    pass
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
            logger.warning(
                "[Crossover Failed] Hybrid factor did not meet threshold or errored."
            )

        return {
            "status": "accepted" if accepted else "rejected",
            "reason": reason,
            "parent_factor_ids": [top1.get("id"), top2.get("id")],
            "factor": result,
        }

    # --- Result Persistence ---

    def _persist_alpha_factors(
        self, factors: list[dict] | None = None
    ) -> list[dict]:
        factors_to_persist = list(
            factors if factors is not None else self.alpha_pool
        )
        return persist_alpha_factors(
            self.db_path,
            self.settings.results_path,
            factors_to_persist,
            run_id=self.run_id,
            trial_sharpes=self.trial_sharpes,
            n_trials=self.n_trials,
        )

    # --- Swarm Execution ---

    def run_swarm(self, parallel=False, log_queue=None):
        try:
            return self._run_swarm_impl(parallel=parallel, log_queue=log_queue)
        except KeyboardInterrupt:
            logger.warning("Swarm run interrupted by user")
            self.execution_tracker.cancel_run(
                self.run_id, reason="KeyboardInterrupt"
            )
            raise
        except Exception as exc:
            self.execution_tracker.fail_run(self.run_id, error_message=str(exc))
            raise

    def _run_swarm_impl(self, parallel=False, log_queue=None):
        with logger.contextualize(**log_context(run_id=self.run_id)):
            # 1. Extract global RiceQuant Auth
            if (
                self.kwargs.get(
                    "data_backend",
                    self.kwargs.get("evaluation_mode", "ricequant"),
                )
                == "ricequant"
            ):
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
            if (
                parallel
                and self.swarm_executor == "process"
                and log_queue is not None
            ):
                worker_log_manager = multiprocessing.Manager()
                worker_log_queue = worker_log_manager.Queue()
                worker_log_thread = threading.Thread(
                    target=_forward_worker_logs,
                    args=(worker_log_queue, log_queue),
                    daemon=True,
                )
                worker_log_thread.start()
                dispatch_log_queue = worker_log_queue

            if self.idempotency_key:
                registered, active_id = self.execution_tracker.register_run(
                    run_id=self.run_id,
                    idempotency_key=self.idempotency_key,
                    config=self.kwargs,
                    total_agents=len(self.researchers),
                )
                if not registered:
                    logger.warning(
                        f"Run with key '{self.idempotency_key}' already "
                        f"exists ({active_id}). Skipping execution."
                    )
                    return self.alpha_pool
            else:
                self.execution_tracker.register_run(
                    run_id=self.run_id,
                    config=self.kwargs,
                    total_agents=len(self.researchers),
                )

            heartbeat = HeartbeatMonitor(
                tracker=self.execution_tracker,
                run_id=self.run_id,
                interval_seconds=5.0,
            )
            heartbeat.start()

            task_log_queue = (
                None
                if parallel and self.swarm_executor == "process"
                else dispatch_log_queue
            )
            self.dispatch_tasks(log_queue=task_log_queue)

            all_results = []
            try:
                if parallel:
                    if self.swarm_executor == "process":
                        max_workers = _process_safe_worker_count(
                            len(self.researchers),
                            self.max_swarm_workers,
                            swarm_executor=self.swarm_executor,
                        )
                    else:
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
                                if self.cancellation_token.is_cancelled():
                                    _cancel_pending_futures(futures, completed)
                                    break
                                completed.add(future)
                                try:
                                    result = future.result()
                                    all_results.append(result)
                                except Exception as exc:
                                    logger.error(
                                        f"Agent generated an exception: {exc}"
                                    )
                        except concurrent.futures.TimeoutError:
                            timed_out = True
                            pending_count = _cancel_pending_futures(
                                futures, completed
                            )
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
                        if max_workers < len(self.researchers):
                            logger.info(
                                f"[Parallel] ProcessPool workers capped to {max_workers}/{len(self.researchers)} "
                                f"(local embedding cap); start jitter 0.5-2.5s."
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
                                    executor.submit(
                                        run_agent_task, kwargs
                                    ): kwargs
                                    for kwargs in self.researchers
                                }
                                for future in concurrent.futures.as_completed(
                                    futures,
                                    timeout=self.swarm_global_timeout,
                                ):
                                    if self.cancellation_token.is_cancelled():
                                        _cancel_pending_futures(
                                            futures, completed
                                        )
                                        break
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
                                            pending_count = (
                                                _cancel_pending_futures(
                                                    futures,
                                                    completed,
                                                )
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
                        if self.cancellation_token.is_cancelled():
                            logger.warning(
                                f"Swarm run {self.run_id} cancelled: "
                                f"{self.cancellation_token.reason}"
                            )
                            break
                        result = run_agent_task(kwargs)
                        all_results.append(result)
                        self.execution_tracker.update_progress(
                            self.run_id,
                            completed_agents=len(all_results),
                        )
            finally:
                heartbeat.stop()
                if worker_log_queue is not None:
                    try:
                        worker_log_queue.put(None)
                    except Exception:
                        pass
                if worker_log_thread is not None:
                    worker_log_thread.join(timeout=2)
                if worker_log_manager is not None:
                    worker_log_manager.shutdown()

            if self.cancellation_token.is_cancelled():
                logger.warning(
                    f"Swarm run {self.run_id} cancelled: "
                    f"{self.cancellation_token.reason}"
                )
                self.execution_tracker.cancel_run(
                    self.run_id, reason=self.cancellation_token.reason
                )
                return self.alpha_pool

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
                        reasoning_effort=self.kwargs.get(
                            "llm_reasoning_effort"
                        ),
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
                        decision = portfolio_agent.select_method(
                            factors_for_portfolio, returns_df
                        )
                        portfolio_result = construct_portfolio(
                            returns_dict, method=decision.method
                        )
                        logger.success(
                            f"Portfolio constructed using {decision.method} | Diversification Ratio: {portfolio_result['diversification_ratio']:.4f}"
                        )

                        # Persist to database
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.cursor()
                            pid = f"portfolio_{uuid.uuid4().hex[:8]}"
                            cursor.execute(
                                """
                                INSERT INTO portfolio_pool (id, run_id, method, rationale, weights_json, returns_json, diversification_ratio)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    pid,
                                    self.run_id,
                                    decision.method,
                                    decision.rationale,
                                    json.dumps(
                                        portfolio_result["weights"],
                                        ensure_ascii=False,
                                    ),
                                    json.dumps(
                                        _serialize_returns(
                                            portfolio_result[
                                                "portfolio_returns"
                                            ]
                                        ),
                                        ensure_ascii=False,
                                    ),
                                    float(
                                        portfolio_result[
                                            "diversification_ratio"
                                        ]
                                    ),
                                ),
                            )
                            conn.commit()
                except Exception as e:
                    logger.error(f"Portfolio construction failed: {e}")
            # ------------------------------

            logger.info(
                f"Swarm execution completed. {len(self.alpha_pool)} "
                f"orthogonal factors found; {len(self.strategy_pool)} "
                "strategies evaluated."
            )
            if self.cancellation_token.is_cancelled():
                self.execution_tracker.cancel_run(
                    self.run_id, reason=self.cancellation_token.reason
                )
            else:
                self.execution_tracker.complete_run(
                    self.run_id,
                    metrics={
                        "factors_count": len(self.alpha_pool),
                        "n_trials": self.n_trials,
                    },
                    factors_count=len(self.alpha_pool),
                )
            return self.alpha_pool

    # --- Strategy Evaluation ---

    def evaluate_strategies(self):
        if not self.alpha_pool:
            self.strategy_pool = []
            return []

        try:
            from aiminer.core.manual_runner import (
                run_manual_strategy_backtest,
                strategy_id_for,
            )
        except Exception as exc:
            logger.warning(
                f"[Strategy Eval] Unable to import strategy runner: {exc}"
            )
            self.strategy_pool = []
            return []

        def _fallback_candidates(factor):
            market_profile = factor.get(
                "market_profile", self.settings.market_profile
            )
            execution_style = str(factor.get("execution_style") or "")
            if market_profile == "futures":
                template_name = (
                    "ts_long_flat"
                    if execution_style == "ts_trend"
                    else "ts_long_short"
                )
            else:
                template_name = (
                    "ts_long_flat"
                    if execution_style == "ts_trend"
                    else "cs_top_bottom"
                )
            cfg = strategy_templates()[template_name].model_copy(
                update={
                    "label": f"{template_name}:{factor.get('hypothesis') or factor.get('id')}",
                    "start_date": self.settings.market_start or "2017-01-01",
                    "end_date": self.settings.market_end or "2020-10-31",
                    "engine": self.settings.evaluation_engine,
                    "market": factor.get(
                        "market_profile", self.settings.market_profile
                    ),
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
                            factor_ic=float(
                                factor.get("perf_metric", 0.0) or 0.0
                            ),
                            walk_forward=(result.get("walk_forward") or {}).get(
                                "aggregate"
                            ),
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
                    factor.get(
                        "selection_score", factor.get("perf_metric", 0.0)
                    ),
                )
                or 0.0
            )

        def _normalize_result(factor, result, idx):
            payload = dict(result)
            payload.setdefault("run_type", "strategy_backtest")
            payload.setdefault("status", "ok")
            payload.setdefault("chart_paths", {})
            payload.setdefault("ran_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
            payload.setdefault(
                "label", (payload.get("strategy_config") or {}).get("label")
            )
            payload.setdefault(
                "market", (payload.get("strategy_config") or {}).get("market")
            )
            payload.setdefault(
                "engine", (payload.get("strategy_config") or {}).get("engine")
            )
            payload["run_id"] = self.run_id
            payload["source_factor_id"] = factor.get("id")
            payload["agent_id"] = factor.get("agent_id")
            payload["candidate_rank"] = int(
                payload.get("candidate_rank", idx) or idx
            )
            raw_strategy_id = payload.get("raw_strategy_id") or payload.get(
                "strategy_id"
            )
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
            payload["market_profile"] = factor.get(
                "market_profile", self.settings.market_profile
            )
            payload["data_backend"] = factor.get(
                "data_backend", self.settings.data_backend
            )
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
                    data_backend=factor.get(
                        "data_backend", self.settings.data_backend
                    ),
                    market_profile=factor.get(
                        "market_profile", self.settings.market_profile
                    ),
                    market_mode=factor.get("market_mode", "single"),
                    market_profiles=[
                        factor.get(
                            "market_profile", self.settings.market_profile
                        )
                    ],
                    local_data_path=self.settings.local_data_path,
                    local_data_layout=self.settings.local_data_layout,
                    run_id=self.run_id,
                    source_factor_id=factor.get("id"),
                    agent_id=factor.get("agent_id"),
                    candidate_rank=idx,
                    template_name=candidate.get("template_name"),
                    rationale=candidate.get("rationale"),
                    signal_multiplier=float(
                        factor.get("signal_direction", 1.0) or 1.0
                    ),
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
                dict(item)
                for item in (factor.get("strategy_results") or [])
                if isinstance(item, dict)
            ]
            best_existing = factor.get("best_strategy_result") or {}
            if best_existing and isinstance(best_existing, dict):
                best_id = best_existing.get("strategy_id")
                if best_id and not any(
                    item.get("strategy_id") == best_id
                    for item in existing_results
                ):
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
                for idx, candidate in enumerate(
                    candidates or _fallback_candidates(factor), start=1
                ):
                    pending_evaluations.append(
                        (factor_idx, factor, idx, candidate)
                    )

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
                        executor.submit(
                            _evaluate_candidate, factor, idx, candidate
                        ): (
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
                            normalized_by_factor.setdefault(
                                factor_idx, []
                            ).append(result)
            else:
                for factor_idx, factor, idx, candidate in pending_evaluations:
                    result = _evaluate_candidate(factor, idx, candidate)
                    if result:
                        normalized_by_factor.setdefault(factor_idx, []).append(
                            result
                        )

        for factor_idx, factor in enumerate(self.alpha_pool):
            normalized_results = sorted(
                normalized_by_factor.get(factor_idx, []),
                key=lambda item: int(item.get("candidate_rank", 0) or 0),
            )
            if not normalized_results:
                factor["strategy_failure_reason"] = (
                    factor.get("strategy_failure_reason")
                    or "no_strategy_results"
                )
                continue

            best = max(
                normalized_results,
                key=lambda item: float(
                    item.get("selection_score", float("-inf")) or float("-inf")
                ),
            )
            best_id = best.get("strategy_id")
            for result in normalized_results:
                result["is_primary"] = bool(
                    best_id and result.get("strategy_id") == best_id
                )
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
                best.get("selection_score", factor.get("perf_metric", 0.0))
                or 0.0
            )
            factor.pop("strategy_failure_reason", None)
            strategy_results.extend(normalized_results)

        self.alpha_pool = sorted(
            self.alpha_pool,
            key=lambda item: (
                float(
                    item.get("selection_score", float("-inf")) or float("-inf")
                ),
                float(item.get("perf_metric", 0.0) or 0.0),
            ),
            reverse=True,
        )
        self.strategy_pool = sorted(
            strategy_results,
            key=lambda item: float(
                item.get("selection_score", float("-inf")) or float("-inf")
            ),
            reverse=True,
        )
        self._dedupe_alpha_pool_by_returns(stage="strategy")
        return self.strategy_pool


def cull_alpha_pool(results_list):
    """IC-threshold + correlation cull used by the swarm manager.

    Same mechanics as ``PortfolioManager.evaluate_and_combine`` without
    constructing LLM/summary agents or opening a results database.
    """
    manager = PortfolioManager.__new__(PortfolioManager)
    manager.alpha_pool = []
    manager.strategy_pool = []
    manager.n_trials = 0
    manager.trial_sharpes = []
    return PortfolioManager.evaluate_and_combine(manager, results_list)


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
        "--roles",
        type=str,
        nargs="+",
        help="Specific roles to assign to sub-agents",
    )
    parser.add_argument(
        "--run-id", type=str, help="Stable run id for checkpoint resume"
    )
    parser.add_argument("--llm-provider", type=str, help="LLM provider")
    parser.add_argument("--llm-model", type=str, help="Specific LLM model name")
    parser.add_argument(
        "--llm-base-url", type=str, help="Override OpenAI-compatible base URL"
    )
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
    parser.add_argument(
        "--local-data-path", type=str, help="Local CSV/Parquet dataset path"
    )
    parser.add_argument(
        "--local-data-layout",
        type=str,
        choices=["auto", "panel", "instrument_files"],
        default="auto",
        help="Local data layout",
    )
    parser.add_argument(
        "--market-start",
        type=str,
        help="Market analysis start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--market-end", type=str, help="Market analysis end date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--use-gpu", action="store_true", help="Use GPU for local RAG embedding"
    )
    parser.add_argument(
        "--rebuild-rag", action="store_true", help="Force rebuild RAG"
    )
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
        from scripts.reset_workspace import (
            build_plan,
            execute_plan,
            render_plan,
            render_result,
        )

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
