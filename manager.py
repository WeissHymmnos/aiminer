import os
import argparse
import pandas as pd
from loguru import logger
import concurrent.futures
from dotenv import load_dotenv

from sub_agent import AlphaResearcher

load_dotenv()

class PortfolioManager:
    def __init__(self, roles=None, **kwargs):
        self.roles = roles or [
            "You are an expert in mean-reversion trading, focusing on short-term price overreactions.",
            "You are an expert in momentum and trend-following, using Moving Averages and MACD.",
            "You are a statistical arbitrage expert, looking for cross-sectional market anomalies."
        ]
        self.researchers = []
        self.alpha_pool = []
        self.kwargs = kwargs

    def dispatch_tasks(self):
        """Instantiate sub-agents with different prior knowledge for physical isolation."""
        for role in self.roles:
            agent = AlphaResearcher(role_prompt=role, **self.kwargs)
            self.researchers.append(agent)

    def evaluate_and_combine(self, results_list):
        """Core logic: survival of the fittest and correlation culling."""
        logger.info("=== Manager Evaluation & Synthesis ===")
        valid_factors = []

        # 1. First-pass filter: Absolute performance threshold
        # Using IC > 0.01 as a reasonable threshold for valid alphas in this mock context
        threshold = 0.01
        for res in results_list:
            if res.get("error"):
                logger.warning(f"[Culled] {res['role'][:30]}... failed with error: {res['error']}")
                continue
                
            perf = res.get("perf_metric", 0.0)
            if perf > threshold:
                valid_factors.append(res)
            else:
                logger.info(f"[Culled] {res['role'][:30]}... generated factor IC ({perf:.4f}) below threshold {threshold}.")

        # 2. Second-pass filter: Correlation (multicollinearity) check
        final_pool = []
        for new_factor in valid_factors:
            is_redundant = False
            new_returns = new_factor.get("returns", pd.Series(dtype=float))
            
            if new_returns.empty:
                logger.warning(f"[Culled] {new_factor['role'][:30]}... has empty returns series.")
                continue

            for existing_factor in final_pool:
                existing_returns = existing_factor.get("returns")
                
                # Align indices to compute correlation
                aligned_df = pd.concat([new_returns, existing_returns], axis=1, join='inner')
                if len(aligned_df) < 5:
                    continue # Not enough overlap, assume uncorrelated
                    
                corr = aligned_df.iloc[:, 0].corr(aligned_df.iloc[:, 1])
                
                if pd.notna(corr) and corr > 0.7:
                    is_redundant = True
                    logger.info(f"[Redundant] {new_factor['role'][:30]}... highly correlated (Corr: {corr:.2f}) with existing factor.")
                    break
            
            if not is_redundant:
                final_pool.append(new_factor)
                logger.success(f"[Accepted] {new_factor['role'][:30]}... (IC: {new_factor['perf_metric']:.4f}) added to Alpha Pool.")

        self.alpha_pool = final_pool
        return self.alpha_pool

    def run_swarm(self, parallel=False):
        self.dispatch_tasks()
        
        all_results = []
        if parallel:
            logger.info("Running sub-agents in PARALLEL mode...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.researchers)) as executor:
                futures = {executor.submit(agent.run): agent for agent in self.researchers}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        all_results.append(result)
                    except Exception as exc:
                        logger.error(f"Agent generated an exception: {exc}")
        else:
            logger.info("Running sub-agents in SERIAL mode...")
            for agent in self.researchers:
                result = agent.run()
                all_results.append(result)
            
        # Manager evaluates all
        self.evaluate_and_combine(all_results)
        
        # Save to results directory
        if self.alpha_pool:
            import json
            os.makedirs("results", exist_ok=True)
            output_path = "results/alpha_pool.json"
            
            serializable_pool = []
            for factor in self.alpha_pool:
                f_copy = factor.copy()
                if "returns" in f_copy and hasattr(f_copy["returns"], "to_dict"):
                    f_copy["returns"] = {str(k.date() if hasattr(k, "date") else k): float(v) for k, v in f_copy["returns"].items()}
                serializable_pool.append(f_copy)
                
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(serializable_pool, f, indent=4, ensure_ascii=False)
            logger.success(f"Final Alpha Pool saved to {output_path}")

        logger.info(f"Swarm execution completed. {len(self.alpha_pool)} orthogonal factors found.")
        return self.alpha_pool

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent AI Alpha Miner - Swarm Manager")
    parser.add_argument("--iterations", type=int, default=2, help="Iterations per sub-agent")
    parser.add_argument("--mode", type=str, choices=["qlib", "ricequant"], default="ricequant", help="Evaluation mode")
    parser.add_argument("--parallel", action="store_true", help="Run sub-agents in parallel")
    parser.add_argument("--roles", type=str, nargs="+", help="Specific roles to assign to sub-agents")
    parser.add_argument("--llm-provider", type=str, help="LLM provider")
    parser.add_argument("--llm-model", type=str, help="Specific LLM model name")
    parser.add_argument("--embedding-provider", type=str, help="Embedding provider for RAG")
    parser.add_argument("--market-start", type=str, help="Market analysis start date (YYYY-MM-DD)")
    parser.add_argument("--market-end", type=str, help="Market analysis end date (YYYY-MM-DD)")
    parser.add_argument("--use-gpu", action="store_true", help="Use GPU for local RAG embedding")
    parser.add_argument("--rebuild-rag", action="store_true", help="Force rebuild RAG")
    args = parser.parse_args()
    
    manager = PortfolioManager(
        roles=args.roles,
        max_iterations=args.iterations,
        evaluation_mode=args.mode,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        embedding_provider=args.embedding_provider,
        market_start=args.market_start,
        market_end=args.market_end,
        use_gpu=args.use_gpu,
        rebuild_rag=args.rebuild_rag
    )
    manager.run_swarm(parallel=args.parallel)
