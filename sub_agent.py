import pandas as pd
from loguru import logger
from workflow.graph import build_workflow
from core.runtime import log_context
from core.settings import AiminerSettings, build_settings


class AlphaResearcher:
    def __init__(
        self,
        role_prompt: str,
        max_iterations: int = 5,
        evaluation_mode: str = "ricequant",
        evaluation_engine: str = "pandas",
        market_start: str = None,
        market_end: str = None,
        llm_provider: str = None,
        llm_model: str = None,
        llm_base_url: str = None,
        embedding_provider: str = None,
        use_gpu: bool = False,
        rebuild_rag: bool = False,
        wiki_bootstrap: bool = False,
        data_backend: str = None,
        market_mode: str = "single",
        market_profile: str = "cn_stock",
        market_profiles=None,
        local_data_path: str = None,
        local_data_layout: str = "auto",
        log_queue=None,
        run_id: str = None,
        agent_id: str = None,
    ):
        self.settings = build_settings(
            {
                "max_iterations": max_iterations,
                "evaluation_mode": evaluation_mode,
                "evaluation_engine": evaluation_engine,
                "market_start": market_start,
                "market_end": market_end,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_base_url": llm_base_url,
                "embedding_provider": embedding_provider,
                "use_gpu": use_gpu,
                "rebuild_rag": rebuild_rag,
                "wiki_bootstrap": wiki_bootstrap,
                "data_backend": data_backend,
                "market_mode": market_mode,
                "market_profile": market_profile,
                "market_profiles": market_profiles,
                "local_data_path": local_data_path,
                "local_data_layout": local_data_layout,
            }
        )
        self.role_prompt = role_prompt
        self.max_iterations = self.settings.max_iterations
        self.evaluation_mode = self.settings.evaluation_mode
        self.evaluation_engine = self.settings.evaluation_engine
        self.market_start = self.settings.market_start
        self.market_end = self.settings.market_end
        self.run_id = run_id
        self.agent_id = agent_id

        # If a log_queue is provided, add a sink to forward logs to the main process
        if log_queue:
            def q_sink(message):
                record = message.record
                log_data = {
                    "level": record["level"].name,
                    "message": record["message"],
                    "role": self.role_prompt[:20],
                    "run_id": record["extra"].get("run_id"),
                    "agent_id": record["extra"].get("agent_id"),
                    "iteration": record["extra"].get("iteration"),
                }
                log_queue.put(log_data)
            logger.add(q_sink, level="INFO", format="{message}")

        logger.info(f"[Sub-Agent] Initializing Role: {self.role_prompt}")

        # Initialize an isolated LangGraph application
        self.app = build_workflow(settings=self.settings)

    def run(self) -> dict:
        """Execute the LangGraph workflow for this researcher."""
        initial_state = {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "llm_provider": self.settings.llm_provider,
            "llm_model": self.settings.llm_model,
            "llm_base_url": self.settings.llm_base_url,
            "iteration": 1,
            "max_iterations": self.max_iterations,
            "role_prompt": self.role_prompt,
            "evaluation_mode": self.evaluation_mode,
            "evaluation_engine": self.evaluation_engine,
            "data_backend": self.settings.data_backend,
            "market_mode": self.settings.market_mode,
            "market_profile": self.settings.market_profile,
            "market_profiles": self.settings.market_profiles,
            "local_data_path": self.settings.local_data_path,
            "local_data_layout": self.settings.local_data_layout,
            "market_analysis_start_date": self.market_start,
            "market_analysis_end_date": self.market_end,
            "best_ic": -999.0,
            "patience_counter": 0,
            "messages": [f"[System] Starting SubAgent with Role: {self.role_prompt}"],
        }

        final_state = initial_state
        logger.info(f"[Sub-Agent] Starting run with role '{self.role_prompt}'")

        try:
            with logger.contextualize(
                **log_context(run_id=self.run_id, agent_id=self.agent_id)
            ):
                for output in self.app.stream(initial_state):
                    for node_name, state_update in output.items():
                        logger.debug(
                            f"[Sub-Agent: {self.role_prompt}] Completed node: {node_name}"
                        )
                        final_state.update(state_update)
                        if "error" in state_update and state_update["error"]:
                            logger.error(
                                f"[Sub-Agent] Error in node {node_name}: {state_update['error']}"
                            )
        except Exception as e:
            logger.error(f"[Sub-Agent] Workflow execution failed: {e}")
            final_state["error"] = f"Workflow exception: {e}"

        metrics = final_state.get("backtest_metrics", {})
        daily_returns_dict = final_state.get("daily_returns", {})

        # Always use IC as the primary selection metric; the manager's
        # threshold (0.01) is calibrated for IC scale, not Sharpe.
        perf_metric = float(metrics.get("information_coefficient", 0.0) or 0.0)

        returns_series = (
            pd.Series(daily_returns_dict)
            if daily_returns_dict
            else pd.Series(dtype=float)
        )
        if not returns_series.empty and pd.api.types.is_string_dtype(
            returns_series.index
        ):
            returns_series.index = pd.to_datetime(
                returns_series.index, format="%Y-%m-%d", errors="coerce"
            )
            n_bad = returns_series.index.isna().sum()
            if n_bad > 0:
                logger.warning(
                    f"[Sub-Agent] Dropped {n_bad} unparseable date(s) from returns series."
                )
                returns_series = returns_series[returns_series.index.notna()]
            returns_series = returns_series.sort_index()

        return {
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "iteration": final_state.get("iteration", self.max_iterations),
            "evaluation_mode": self.evaluation_mode,
            "evaluation_engine": self.evaluation_engine,
            "llm_provider": self.settings.llm_provider,
            "llm_model": self.settings.llm_model,
            "llm_base_url": self.settings.llm_base_url,
            "data_backend": self.settings.data_backend,
            "market_mode": self.settings.market_mode,
            "market_profile": self.settings.market_profile,
            "market_profiles": self.settings.market_profiles,
            "role": self.role_prompt,
            "hypothesis": final_state.get("hypothesis_name"),
            "code": final_state.get("code_expression"),
            "metrics": metrics,
            "perf_metric": perf_metric,
            "returns": returns_series,
            "strategy_results": final_state.get("strategy_results", []),
            "best_strategy_result": final_state.get("best_strategy_result"),
            "best_strategy_config": final_state.get("best_strategy_config"),
            "best_strategy_metrics": final_state.get("best_strategy_metrics"),
            "best_strategy_id": final_state.get("best_strategy_id"),
            "strategy_daily_returns": final_state.get("strategy_daily_returns", {}),
            "selection_score": final_state.get("selection_score", 0.0),
            "execution_style": final_state.get("execution_style"),
            "strategy_failure_reason": final_state.get("strategy_failure_reason"),
            "is_effective": final_state.get("is_effective", False),
            "is_simulated": final_state.get("is_simulated", False),
            "error": final_state.get("error"),
        }
