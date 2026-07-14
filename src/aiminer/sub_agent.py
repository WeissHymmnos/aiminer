from loguru import logger
from aiminer.app_workflow.graph import build_workflow
from aiminer.core.agent_result import (
    factor_result_view as _factor_result_view,
    state_to_agent_result,
)
from aiminer.core.agent_checkpoint import load_agent_checkpoints
from aiminer.core.constants import MISSING_IC_SENTINEL
from aiminer.core.runtime import log_context
from aiminer.core.settings import AiminerSettings, build_settings

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
        llm_reasoning_effort: str = None,
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
        disable_early_stop: bool = False,
        settings: AiminerSettings | None = None,
    ):
        self.settings = settings or build_settings(
            {
                "max_iterations": max_iterations,
                "evaluation_mode": evaluation_mode,
                "evaluation_engine": evaluation_engine,
                "market_start": market_start,
                "market_end": market_end,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_base_url": llm_base_url,
                "llm_reasoning_effort": llm_reasoning_effort,
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
                "disable_early_stop": disable_early_stop,
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
            "llm_reasoning_effort": self.settings.llm_reasoning_effort,
            "iteration": 1,
            "max_iterations": self.max_iterations,
            "disable_early_stop": self.settings.disable_early_stop,
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
            "best_ic": MISSING_IC_SENTINEL,
            "best_ic_abs": -1.0,
            "best_factor_snapshot": None,
            "patience_counter": 0,
            "messages": [f"[System] Starting SubAgent with Role: {self.role_prompt}"],
        }

        final_state = initial_state
        logger.info(f"[Sub-Agent] Starting run with role '{self.role_prompt}'")

        checkpoint = self._load_resume_checkpoint()
        if checkpoint:
            iteration = int(checkpoint.get("iteration") or 0)
            if iteration >= self.max_iterations:
                logger.info(
                    f"[Sub-Agent] Checkpoint already reached max_iterations={self.max_iterations}; "
                    "returning recovered result."
                )
                return checkpoint
            initial_state.update(self._checkpoint_to_initial_state(checkpoint))
            logger.info(
                f"[Sub-Agent] Resuming from checkpoint at iteration {iteration}; "
                f"next iteration {initial_state['iteration']}."
            )

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

        return state_to_agent_result(
            final_state,
            settings=self.settings,
            role_prompt=self.role_prompt,
            run_id=self.run_id,
            agent_id=self.agent_id,
            max_iterations=self.max_iterations,
        )

    def _load_resume_checkpoint(self) -> dict | None:
        if not self.run_id or not self.agent_id:
            return None
        try:
            checkpoints = load_agent_checkpoints(self.settings.db_path, self.run_id)
        except Exception as exc:
            logger.warning(f"[Sub-Agent] Failed to load checkpoint: {exc}")
            return None
        for checkpoint in checkpoints:
            if checkpoint.get("agent_id") == self.agent_id and not checkpoint.get("error"):
                return checkpoint
        return None

    def _checkpoint_to_initial_state(self, checkpoint: dict) -> dict:
        metrics = checkpoint.get("metrics") or {}
        ic = float(metrics.get("information_coefficient", 0.0) or 0.0)
        iteration = int(checkpoint.get("iteration") or 0)
        snapshot = {
            "iteration": iteration,
            "hypothesis": checkpoint.get("hypothesis"),
            "hypothesis_name": checkpoint.get("hypothesis"),
            "code": checkpoint.get("code"),
            "code_expression": checkpoint.get("code"),
            "metrics": metrics,
            "returns": checkpoint.get("returns") or {},
            "daily_returns": checkpoint.get("returns") or {},
            "plot_paths": checkpoint.get("plot_paths") or {},
            "strategy_candidates": checkpoint.get("strategy_candidates") or [],
            "strategy_results": checkpoint.get("strategy_results") or [],
            "best_strategy_result": checkpoint.get("best_strategy_result"),
            "best_strategy_config": checkpoint.get("best_strategy_config"),
            "best_strategy_metrics": checkpoint.get("best_strategy_metrics"),
            "best_strategy_id": checkpoint.get("best_strategy_id"),
            "strategy_daily_returns": checkpoint.get("strategy_daily_returns") or {},
            "selection_score": checkpoint.get("selection_score", 0.0),
            "execution_style": checkpoint.get("execution_style"),
            "strategy_failure_reason": checkpoint.get("strategy_failure_reason"),
            "is_effective": checkpoint.get("is_effective", False),
            "is_simulated": checkpoint.get("is_simulated", False),
            "ic_direction": checkpoint.get("ic_direction"),
            "ic_direction_label": checkpoint.get("ic_direction_label"),
        }
        return {
            "iteration": min(iteration + 1, self.max_iterations),
            "best_ic": ic,
            "best_ic_abs": abs(ic),
            "best_code_expression": checkpoint.get("code"),
            "best_factor_snapshot": snapshot,
            "messages": [
                f"[System] Resuming SubAgent with Role: {self.role_prompt}",
                f"[Checkpoint] Resumed after iteration {iteration}.",
            ],
        }
