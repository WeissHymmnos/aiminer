import os
import argparse
import pandas as pd
from loguru import logger
import concurrent.futures
from dotenv import load_dotenv
import multiprocessing
import time
import random

import sqlite3
import json
import uuid

from sub_agent import AlphaResearcher
from agents.summary_agent import SummaryAgent
from core.alphaeval.rq_eval import init_rq_auth
from core.runtime import log_context, new_agent_id, new_run_id
from core.settings import build_settings
from core.strategy import ensure_strategy_table, persist_strategy_result, strategy_templates


# Global entry point for multiprocessing
def run_agent_task(kwargs):
    # Add a small random jitter to avoid simultaneous DB file access
    time.sleep(random.uniform(0.1, 1.0))
    agent = AlphaResearcher(**kwargs)
    return agent.run()


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


load_dotenv()


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
        self.run_id = kwargs.get("run_id") or new_run_id()
        self.summary_agent = SummaryAgent(
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
        )
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for long-term factor tracking.

        Schema carries the full factor detail (metrics/returns/is_effective)
        so the HTTP API never needs to cross-check against the JSON backup.
        """
        os.makedirs("results", exist_ok=True)
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
            conn.commit()
        ensure_strategy_table(self.db_path)
        self._backfill_from_json()

    def _backfill_from_json(self):
        """One-shot backfill: populate extended columns for rows created
        before the schema change, pulling data from results/alpha_pool.json
        when the id still matches. Rows with no match remain NULL — the
        frontend handles that gracefully."""
        json_path = "results/alpha_pool.json"
        if not os.path.exists(json_path):
            return

        # Fast path: if every row already has metrics_json populated, skip entirely.
        with sqlite3.connect(self.db_path) as conn:
            null_count = conn.execute(
                "SELECT COUNT(*) FROM alpha_pool WHERE metrics_json IS NULL"
            ).fetchone()[0]
        if null_count == 0:
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
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
        # A-share real effective factors typically have IC in 0.003~0.008;
        # lowered from 0.01 to 0.005 to avoid culling genuinely useful alphas.
        threshold = 0.005
        for res in results_list:
            if res.get("error"):
                logger.warning(
                    f"[Rejected:error] {res['role'][:30]}... failed with error: {res['error']}"
                )
                continue

            perf = res.get("perf_metric", 0.0)
            if perf > threshold:
                valid_factors.append(res)
            else:
                logger.info(
                    f"[Rejected:threshold] {res['role'][:30]}... generated factor IC ({perf:.4f}) below threshold {threshold}."
                )

        # 2. Second-pass filter: Correlation (multicollinearity) check
        final_pool = []
        for new_factor in valid_factors:
            is_redundant = False
            new_returns = new_factor.get("returns", pd.Series(dtype=float))

            if new_returns.empty:
                logger.warning(
                    f"[Rejected:empty_returns] {new_factor['role'][:30]}... has empty returns series."
                )
                continue

            for existing_factor in final_pool:
                existing_returns = existing_factor.get("returns")
                if existing_returns is None or (
                    hasattr(existing_returns, "empty") and existing_returns.empty
                ):
                    continue

                # Align indices and drop NaN pairs before computing correlation
                aligned_df = pd.concat(
                    [new_returns, existing_returns], axis=1, join="inner"
                ).dropna()
                if len(aligned_df) < 10:
                    continue  # Not enough clean overlap; treat as uncorrelated

                corr = aligned_df.iloc[:, 0].corr(aligned_df.iloc[:, 1])

                same_market = (
                    new_factor.get("market_profile") == existing_factor.get("market_profile")
                )
                if same_market and pd.notna(corr) and corr > 0.7:
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

        self.alpha_pool = final_pool
        return self.alpha_pool

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
                from core.hybrid_knowledge import HybridKnowledge

                logger.info(
                    "Main process synthesizing shared knowledge base (LLM Wiki)..."
                )
                knowledge = HybridKnowledge(
                    llm_provider=self.kwargs.get("llm_provider"),
                    llm_model=self.kwargs.get("llm_model"),
                    embedding_provider=self.kwargs.get("embedding_provider"),
                    llm_base_url=self.kwargs.get("llm_base_url"),
                )
                knowledge.bootstrap_wiki(force=False)

            self.dispatch_tasks(log_queue=log_queue)

            all_results = []
            if parallel:
                logger.info("Running sub-agents in PARALLEL mode (Multi-Process)...")
                try:
                    with concurrent.futures.ProcessPoolExecutor(
                        max_workers=len(self.researchers)
                    ) as executor:
                        futures = {
                            executor.submit(run_agent_task, kwargs): kwargs
                            for kwargs in self.researchers
                        }
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                result = future.result(timeout=600)
                                all_results.append(result)
                            except concurrent.futures.TimeoutError:
                                logger.error("Agent timed out after 600s — skipping.")
                            except Exception as exc:
                                logger.error(f"Agent generated an exception: {exc}")
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

            # Manager evaluates all
            self.evaluate_and_combine(all_results)
            self.evaluate_strategies()

            # --- Genetic Algorithm Crossover ---
            if len(self.alpha_pool) >= 2:
                logger.info("=== Manager Genetic Crossover ===")
                sorted_pool = sorted(
                    self.alpha_pool,
                    key=lambda x: x.get("perf_metric", 0.0),
                    reverse=True,
                )
                top1, top2 = sorted_pool[0], sorted_pool[1]

                crossover_role = (
                    "You are an AI Genetic Crossover Expert. Your task is to combine two high-performing alpha factors into a single, "
                    "superior hybrid factor. You excel at extracting orthogonal components and merging them logically.\n"
                    "Here are the two parent factors:\n"
                    f"Parent 1 (IC: {top1['perf_metric']:.4f}): {top1['hypothesis']}\nCode: {top1['code']}\n\n"
                    f"Parent 2 (IC: {top2['perf_metric']:.4f}): {top2['hypothesis']}\nCode: {top2['code']}\n\n"
                    "Extract the best ideas from both and synthesize a new Alpha factor."
                )

                logger.info("Spawning Crossover Agent...")
                crossover_kwargs = dict(self.kwargs)
                crossover_kwargs["role_prompt"] = crossover_role
                crossover_kwargs["run_id"] = self.run_id
                crossover_kwargs["agent_id"] = "agent_crossover"
                crossover_result = run_agent_task(crossover_kwargs)

                if (
                    not crossover_result.get("error")
                    and crossover_result.get("perf_metric", 0.0) > 0.01
                ):
                    is_redundant = False
                    new_returns = crossover_result.get("returns", pd.Series(dtype=float))
                    if not new_returns.empty:
                        for existing_factor in self.alpha_pool:
                            existing_returns = existing_factor.get("returns")
                            if existing_returns is None or (
                                hasattr(existing_returns, "empty")
                                and existing_returns.empty
                            ):
                                continue
                            aligned_df = pd.concat(
                                [new_returns, existing_returns], axis=1, join="inner"
                            ).dropna()
                            if len(aligned_df) >= 10:
                                corr = aligned_df.iloc[:, 0].corr(aligned_df.iloc[:, 1])
                                if pd.notna(corr) and corr > 0.7:
                                    is_redundant = True
                                    break
                    if not is_redundant:
                        logger.success(
                            f"[Crossover Success] Hybrid factor IC: {crossover_result['perf_metric']:.4f}"
                        )
                        crossover_result["id"] = f"alpha_{uuid.uuid4().hex[:8]}"
                        self.alpha_pool.append(crossover_result)
                    else:
                        logger.warning(
                            "[Crossover Failed] Hybrid factor is highly correlated with existing factors in the same market."
                        )
                else:
                    logger.warning(
                        "[Crossover Failed] Hybrid factor did not meet threshold or errored."
                    )
            # -----------------------------------

            # 3. Final Step: Generate Reports and Persistent Storage
            if self.alpha_pool:
                logger.info(
                    f"Generating reports and persisting {len(self.alpha_pool)} factors..."
                )
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    for factor in self.alpha_pool:
                        report_path = self.summary_agent.generate_markdown_report(factor)
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
                                     run_id, agent_id, iteration, evaluation_mode,
                                     evaluation_engine, data_backend, market_mode, market_profile,
                                     llm_provider, llm_model, is_simulated)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                # with-block exits here → single fsync for all inserts.

            # Legacy JSON Backup (SQLite is the source of truth; this file
            # is kept for convenience / debugging.)
                output_path = "results/alpha_pool.json"
                serializable_pool = []
                for factor in self.alpha_pool:
                    f_copy = factor.copy()
                    f_copy["returns"] = _serialize_returns(f_copy.get("returns"))
                    serializable_pool.append(f_copy)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_pool, f, indent=4, ensure_ascii=False)
                logger.success(f"Final Alpha Pool saved to {output_path} and SQLite.")

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

            logger.info(
                f"Swarm execution completed. {len(self.alpha_pool)} orthogonal factors found; {len(self.strategy_pool)} strategies evaluated."
            )
            return self.alpha_pool

    def evaluate_strategies(self):
        if not self.alpha_pool:
            self.strategy_pool = []
            return []

        try:
            from core.manual_runner import run_manual_strategy_backtest
        except Exception as exc:
            logger.warning(f"[Strategy Eval] Unable to import strategy runner: {exc}")
            self.strategy_pool = []
            return []

        selected_templates = [
            "cs_top_bottom",
            "cs_top_only",
            "ts_long_flat",
            "ts_long_short",
        ]
        strategy_results = []
        for factor in self.alpha_pool:
            expression = factor.get("code")
            if not expression:
                continue
            for template_name in selected_templates:
                cfg = strategy_templates()[template_name].model_copy(
                    update={
                        "label": f"{template_name}:{factor.get('hypothesis') or factor.get('id')}",
                        "start_date": self.settings.market_start or "2017-01-01",
                        "end_date": self.settings.market_end or "2020-10-31",
                        "engine": self.settings.evaluation_engine,
                        "market": factor.get("market_profile", self.settings.market_profile),
                    }
                )
                try:
                    result = run_manual_strategy_backtest(
                        expression,
                        cfg.model_dump(mode="json"),
                        data_backend=factor.get("data_backend", self.settings.data_backend),
                        market_profile=factor.get("market_profile", self.settings.market_profile),
                        market_mode=factor.get("market_mode", "single"),
                        market_profiles=[factor.get("market_profile", self.settings.market_profile)],
                        local_data_path=self.settings.local_data_path,
                        local_data_layout=self.settings.local_data_layout,
                    )
                except Exception as exc:
                    logger.warning(
                        f"[Strategy Eval] {template_name} failed for factor '{factor.get('hypothesis', '?')}': {exc}"
                    )
                    continue
                result["run_id"] = self.run_id
                result["source_factor_id"] = factor.get("id")
                strategy_results.append(result)
        self.strategy_pool = strategy_results
        return self.strategy_pool


if __name__ == "__main__":
    # Use 'spawn' instead of 'fork' to prevent deadlocks with AI libraries/DB locks
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
    parser.add_argument("--llm-provider", type=str, help="LLM provider")
    parser.add_argument("--llm-model", type=str, help="Specific LLM model name")
    parser.add_argument("--llm-base-url", type=str, help="Override OpenAI-compatible base URL")
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
        default="cn_stock",
        help="Market profile for this run",
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
    args = parser.parse_args()

    manager = PortfolioManager(
        roles=args.roles,
        max_iterations=args.iterations,
        evaluation_mode=args.mode,
        data_backend=args.data_backend,
        evaluation_engine=args.engine,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
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
    )
    manager.run_swarm(parallel=args.parallel)
