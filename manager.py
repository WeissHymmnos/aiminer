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
        self.roles = roles or [
            "You are an expert in mean-reversion trading, focusing on short-term price overreactions.",
            "You are an expert in momentum and trend-following, using Moving Averages and MACD.",
            "You are a statistical arbitrage expert, looking for cross-sectional market anomalies.",
        ]
        self.researchers = []
        self.alpha_pool = []
        self.kwargs = kwargs
        self.summary_agent = SummaryAgent(
            provider=kwargs.get("llm_provider"), model=kwargs.get("llm_model")
        )
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for long-term factor tracking.

        Schema carries the full factor detail (metrics/returns/is_effective)
        so the HTTP API never needs to cross-check against the JSON backup.
        """
        os.makedirs("results", exist_ok=True)
        self.db_path = "results/alpha_miner.db"
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
                    perf_metric REAL
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_alpha_timestamp ON alpha_pool(timestamp)"
            )
            # Idempotent migration for pre-existing databases created before
            # the extended schema landed.
            for col, ddl in [
                ("metrics_json", "ALTER TABLE alpha_pool ADD COLUMN metrics_json TEXT"),
                ("returns_json", "ALTER TABLE alpha_pool ADD COLUMN returns_json TEXT"),
                ("is_effective", "ALTER TABLE alpha_pool ADD COLUMN is_effective INTEGER"),
                ("perf_metric",  "ALTER TABLE alpha_pool ADD COLUMN perf_metric REAL"),
            ]:
                try:
                    cursor.execute(ddl)
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()
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
        for role in self.roles:
            task_kwargs = dict(self.kwargs)
            task_kwargs["role_prompt"] = role
            if log_queue:
                task_kwargs["log_queue"] = log_queue
            self.researchers.append(task_kwargs)

    def evaluate_and_combine(self, results_list):
        """Core logic: survival of the fittest and correlation culling."""
        logger.info("=== Manager Evaluation & Synthesis ===")
        valid_factors = []

        # 1. First-pass filter: Absolute performance threshold
        # Using IC > 0.01 as a reasonable threshold for valid alphas in this mock context
        threshold = 0.01
        for res in results_list:
            if res.get("error"):
                logger.warning(
                    f"[Culled] {res['role'][:30]}... failed with error: {res['error']}"
                )
                continue

            perf = res.get("perf_metric", 0.0)
            if perf > threshold:
                valid_factors.append(res)
            else:
                logger.info(
                    f"[Culled] {res['role'][:30]}... generated factor IC ({perf:.4f}) below threshold {threshold}."
                )

        # 2. Second-pass filter: Correlation (multicollinearity) check
        final_pool = []
        for new_factor in valid_factors:
            is_redundant = False
            new_returns = new_factor.get("returns", pd.Series(dtype=float))

            if new_returns.empty:
                logger.warning(
                    f"[Culled] {new_factor['role'][:30]}... has empty returns series."
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

                if pd.notna(corr) and corr > 0.7:
                    is_redundant = True
                    logger.info(
                        f"[Redundant] {new_factor['role'][:30]}... highly correlated (Corr: {corr:.2f}) with existing factor."
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

    def run_swarm(self, parallel=False):
        # 1. Extract global RiceQuant Auth
        if self.kwargs.get("evaluation_mode", "ricequant") == "ricequant":
            logger.info("Initializing Global RiceQuant Auth...")
            try:
                init_rq_auth()
            except Exception as e:
                logger.error(f"Global RiceQuant Auth failed: {e}")

        # 2. Shared Wiki Initialization (Once per swarm run)
        if self.kwargs.get("wiki_bootstrap"):
            from core.hybrid_knowledge import HybridKnowledge

            logger.info(
                "🚀 Main process synthesizing shared knowledge base (LLM Wiki)..."
            )
            knowledge = HybridKnowledge(
                llm_provider=self.kwargs.get("llm_provider"),
                llm_model=self.kwargs.get("llm_model"),
                embedding_provider=self.kwargs.get("embedding_provider"),
            )
            knowledge.bootstrap_wiki(force=False)

        self.dispatch_tasks()

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
                raise  # context manager __exit__ already calls shutdown
        else:
            logger.info("Running sub-agents in SERIAL mode...")
            for kwargs in self.researchers:
                result = run_agent_task(kwargs)
                all_results.append(result)

        # Manager evaluates all
        self.evaluate_and_combine(all_results)

        # --- Genetic Algorithm Crossover ---
        if len(self.alpha_pool) >= 2:
            logger.info("=== Manager Genetic Crossover ===")
            # Sort by IC
            sorted_pool = sorted(
                self.alpha_pool, key=lambda x: x.get("perf_metric", 0.0), reverse=True
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
            crossover_result = run_agent_task(crossover_kwargs)

            if (
                not crossover_result.get("error")
                and crossover_result.get("perf_metric", 0.0) > 0.01
            ):
                # Correlation check against existing pool
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
                        "[Crossover Failed] Hybrid factor is highly correlated with existing factors."
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
                    # Generate MD Report & Chart
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
                                 metrics_json, returns_json, is_effective, perf_metric)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                                int(is_effective) if isinstance(is_effective, bool) else is_effective,
                                factor.get("perf_metric"),
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

        logger.info(
            f"Swarm execution completed. {len(self.alpha_pool)} orthogonal factors found."
        )
        return self.alpha_pool


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
    parser.add_argument(
        "--embedding-provider", type=str, help="Embedding provider for RAG"
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
        evaluation_engine=args.engine,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        embedding_provider=args.embedding_provider,
        market_start=args.market_start,
        market_end=args.market_end,
        use_gpu=args.use_gpu,
        rebuild_rag=args.rebuild_rag,
        wiki_bootstrap=args.wiki_bootstrap,
    )
    manager.run_swarm(parallel=args.parallel)
