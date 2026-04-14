import pandas as pd
from loguru import logger
from workflow.graph import build_workflow

class AlphaResearcher:
    def __init__(
        self, 
        role_prompt: str, 
        max_iterations: int = 3, 
        evaluation_mode: str = "ricequant",
        market_start: str = None,
        market_end: str = None,
        market_lookback: int = 365,
        llm_provider: str = None,
        llm_model: str = None,
        embedding_provider: str = None,
        use_gpu: bool = False,
        rebuild_rag: bool = False
    ):
        self.role_prompt = role_prompt
        self.max_iterations = max_iterations
        self.evaluation_mode = evaluation_mode
        self.market_start = market_start
        self.market_end = market_end
        self.market_lookback = market_lookback
        
        logger.info(f"[Sub-Agent] Initializing Role: {self.role_prompt}")
        
        # Initialize an isolated LangGraph application
        self.app = build_workflow(
            rebuild_rag=rebuild_rag,
            llm_provider=llm_provider,
            llm_model=llm_model,
            embedding_provider=embedding_provider,
            use_gpu=use_gpu
        )

    def run(self) -> dict:
        """Execute the LangGraph workflow for this researcher."""
        initial_state = {
            "iteration": 1,
            "max_iterations": self.max_iterations,
            "role_prompt": self.role_prompt,
            "evaluation_mode": self.evaluation_mode,
            "market_analysis_start_date": self.market_start,
            "market_analysis_end_date": self.market_end,
            "market_analysis_lookback_days": self.market_lookback,
            "messages": [f"[System] Starting SubAgent with Role: {self.role_prompt}"]
        }

        final_state = initial_state
        logger.info(f"[Sub-Agent] Starting run with role '{self.role_prompt}'")
        
        try:
            for output in self.app.stream(initial_state):
                for node_name, state_update in output.items():
                    logger.debug(f"[Sub-Agent: {self.role_prompt}] Completed node: {node_name}")
                    final_state.update(state_update)
                    if "error" in state_update and state_update["error"]:
                        logger.error(f"[Sub-Agent] Error in node {node_name}: {state_update['error']}")
        except Exception as e:
            logger.error(f"[Sub-Agent] Workflow execution failed: {e}")

        metrics = final_state.get("backtest_metrics", {})
        daily_returns_dict = final_state.get("daily_returns", {})
        
        # For filtering, we'll use Information Coefficient (IC) as a proxy for 'Sharpe' if Sharpe is not available
        perf_metric = metrics.get("information_coefficient", 0.0)
        if "Sharpe" in metrics:
            perf_metric = metrics["Sharpe"]
            
        returns_series = pd.Series(daily_returns_dict) if daily_returns_dict else pd.Series(dtype=float)
        if not returns_series.empty and pd.api.types.is_string_dtype(returns_series.index):
            returns_series.index = pd.to_datetime(returns_series.index)
            returns_series = returns_series.sort_index()

        return {
            "role": self.role_prompt,
            "hypothesis": final_state.get("hypothesis_name"),
            "code": final_state.get("code_expression"),
            "metrics": metrics,
            "perf_metric": perf_metric,
            "returns": returns_series,
            "is_effective": final_state.get("is_effective", False),
            "error": final_state.get("error")
        }
