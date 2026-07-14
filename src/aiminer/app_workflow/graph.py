from __future__ import annotations
from langgraph.graph import StateGraph, END
from loguru import logger
import time
from aiminer.app_workflow.state import AlphaMinerState
from aiminer.agents.idea_agent import IdeaAgent
from aiminer.agents.factor_agent import FactorAgent
from aiminer.agents.eval_agent import EvalAgent
from aiminer.agents.strategy_agent import StrategyAgent
from aiminer.agents.strategy_critic import (
    DEFAULT_MAX_REFINEMENT_ROUNDS,
    StrategyCritic,
    _improvement_satisfied,
)
from aiminer.core.agent_checkpoint import persist_agent_checkpoint
from aiminer.core.constants import (
    DEFAULT_PATIENCE,
    EXCEPTIONAL_IC_THRESHOLD,
    IC_ACCEPT_THRESHOLD,
    MISSING_IC_SENTINEL,
)
from aiminer.core.hybrid_knowledge import HybridKnowledge
from aiminer.core.settings import AiminerSettings, build_settings


# Routing Functions
def _state_has_evaluation_failure(state: AlphaMinerState) -> bool:
    metrics = state.get("backtest_metrics", {}) or {}
    return bool(
        state.get("evaluation_failed")
        or state.get("_evaluation_failed")
        or metrics.get("evaluation_failed")
        or metrics.get("_evaluation_failed")
    )


def route_after_idea(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("hypothesis_name"):
        logger.error(
            "[Router] hypothesis_name missing after idea_agent — ending workflow."
        )
        return "end"
    return "factor_agent"


def route_after_factor(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("code_expression"):
        logger.error(
            "[Router] code_expression missing after factor_agent — ending workflow."
        )
        return "end"
    if not state.get("is_valid_syntax", True):
        logger.warning(
            "[Router] Invalid syntax detected — skipping to eval with caveat."
        )
    return "eval_agent"


def route_after_eval(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "end"
    metrics = state.get("backtest_metrics", {}) or {}
    current_ic = float(metrics.get("information_coefficient", 0.0) or 0.0)
    if state.get("is_simulated", False):
        return "wiki_update"
    if current_ic >= IC_ACCEPT_THRESHOLD and state.get("code_expression"):
        return "strategy_agent"
    return "wiki_update"


def route_after_strategy(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "wiki_update"
    if not state.get("strategy_candidates"):
        return "wiki_update"
    return "strategy_eval"


def route_after_strategy_eval(state: AlphaMinerState) -> str:
    """Decide whether to invoke the critic for a refinement round or finalize.

    Mirrors StrategyCritic's halt logic so we don't pay for an LLM call when
    we already know it would short-circuit. Errors and empty results bypass
    the critic entirely.
    """
    if state.get("error"):
        return "wiki_update"
    if state.get("strategy_failure_reason"):
        return "wiki_update"
    if not state.get("best_strategy_result"):
        return "wiki_update"
    round_idx = int(state.get("strategy_refinement_round", 0))
    max_rounds = int(
        state.get("max_strategy_refinement_rounds", DEFAULT_MAX_REFINEMENT_ROUNDS)
    )
    if max_rounds <= 0:
        return "wiki_update"
    if round_idx >= max_rounds:
        return "wiki_update"
    history = state.get("strategy_refinement_history") or []
    previous_score = history[-1].get("selection_score") if history else None
    current_score = float(state.get("selection_score", 0.0) or 0.0)
    if not _improvement_satisfied(current_score, previous_score):
        return "wiki_update"
    return "strategy_critic"


def route_after_strategy_critic(state: AlphaMinerState) -> str:
    """If the critic produced a fresh candidate batch we re-evaluate;
    otherwise we hand off to wiki_update with the current best."""
    if state.get("error"):
        return "wiki_update"
    history = state.get("strategy_refinement_history") or []
    if history and history[-1].get("halt_reason"):
        return "wiki_update"
    if not state.get("strategy_candidates"):
        return "wiki_update"
    return "strategy_eval"


def route_after_wiki(state: AlphaMinerState) -> str:
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 1)
    disable_early_stop = bool(state.get("disable_early_stop", False))

    metrics = state.get("backtest_metrics", {})
    current_ic = metrics.get("information_coefficient", 0.0)
    is_simulated = state.get("is_simulated", False)

    # 1. Early Stopping: High IC achieved — only on real (non-simulated) data
    is_simulated = state.get("is_simulated", False)
    if current_ic >= EXCEPTIONAL_IC_THRESHOLD and not is_simulated and not disable_early_stop:
        logger.success(f"[Early Stop] Exceptional IC reached: {current_ic:.4f}")
        return "end"
    if current_ic >= EXCEPTIONAL_IC_THRESHOLD and not is_simulated and disable_early_stop:
        logger.info(
            f"[Router] IC={current_ic:.4f} reached early-stop threshold, "
            "but disable_early_stop=True; continuing."
        )
    if current_ic >= EXCEPTIONAL_IC_THRESHOLD and is_simulated:
        logger.warning(
            f"[Router] IC={current_ic:.4f} looks exceptional but metrics are SIMULATED — "
            "ignoring early stop trigger and continuing."
        )

    # 2. Early Stopping: Patience exhausted
    patience = state.get("patience_counter", 0)
    if patience >= DEFAULT_PATIENCE and not disable_early_stop:
        logger.info(
            f"[Early Stop] No IC improvement for {DEFAULT_PATIENCE} consecutive iterations."
        )
        return "end"
    if patience >= DEFAULT_PATIENCE and disable_early_stop:
        logger.info(
            f"[Router] Patience counter={patience} reached early-stop threshold, "
            "but disable_early_stop=True; continuing."
        )

    if iteration < max_iterations:
        return "increment"
    return "end"


def increment_iteration(state: AlphaMinerState):
    return {
        "iteration": state.get("iteration", 1) + 1,
        "best_ic": state.get("best_ic", MISSING_IC_SENTINEL),
        "best_ic_abs": state.get("best_ic_abs", -1.0),
        "best_code_expression": state.get(
            "best_code_expression", state.get("code_expression")
        ),
        "best_factor_snapshot": state.get("best_factor_snapshot"),
        "patience_counter": state.get("patience_counter", 0),
        "error": None,
        "is_valid_syntax": True,
        # Clear per-iteration agent outputs to prevent state pollution
        "hypothesis_name": None,
        "hypothesis_description": None,
        "rationale": None,
        "code_expression": None,
        "syntax_error": None,
        "math_formula": None,
        "variables_defined": None,
        "backtest_metrics": None,
        "factor_metrics": None,
        "daily_returns": None,
        "plot_paths": None,
        "review_summary": None,
        "is_effective": None,
        "factor_is_effective": None,
        "is_simulated": False,
        "evaluation_failed": False,
        "evaluation_error": None,
        "ic_direction": None,
        "ic_direction_label": None,
        "suggested_improvements": None,
        "strategy_candidates": [],
        "strategy_results": [],
        "best_strategy_config": None,
        "best_strategy_metrics": None,
        "best_strategy_id": None,
        "best_strategy_result": None,
        "strategy_daily_returns": None,
        "execution_style": None,
        "strategy_failure_reason": None,
        "selection_score": 0.0,
        "strategy_refinement_round": 0,
        "strategy_refinement_history": [],
    }


def _merge_strategy_update_into_best_snapshot(
    state: AlphaMinerState, update: dict
) -> dict:
    """Attach strategy-stage outputs to the factor snapshot for this iteration.

    The manager can then receive the best factor's complete state even when a
    later iteration finishes last.
    """
    snapshot = state.get("best_factor_snapshot")
    if not snapshot:
        return update
    if snapshot.get("iteration") != state.get("iteration"):
        return update
    if snapshot.get("code_expression") != state.get("code_expression"):
        return update

    merged = dict(snapshot)
    merged["strategy_candidates"] = state.get("strategy_candidates", [])
    for key in (
        "strategy_results",
        "best_strategy_result",
        "best_strategy_config",
        "best_strategy_metrics",
        "best_strategy_id",
        "strategy_daily_returns",
        "selection_score",
        "execution_style",
        "strategy_failure_reason",
    ):
        if key in update:
            merged[key] = update.get(key)
        elif key in state:
            merged[key] = state.get(key)
    return {**update, "best_factor_snapshot": merged}


def build_workflow(
    settings: AiminerSettings | None = None,
    rebuild_rag: bool = False,
    llm_provider: str = None,
    llm_model: str = None,
    llm_reasoning_effort: str = None,
    embedding_provider: str = None,
    use_gpu: bool = False,
):
    settings = settings or build_settings(
        {
            "rebuild_rag": rebuild_rag,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_reasoning_effort": llm_reasoning_effort,
            "embedding_provider": embedding_provider,
            "use_gpu": use_gpu,
        }
    )

    # Initialize shared knowledge base
    knowledge = HybridKnowledge(settings=settings)

    # Initialize agents
    idea_agent = IdeaAgent(
        knowledge,
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        reasoning_effort=settings.llm_reasoning_effort,
    )
    factor_agent = FactorAgent(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        reasoning_effort=settings.llm_reasoning_effort,
    )
    eval_agent = EvalAgent(
        knowledge,
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        reasoning_effort=settings.llm_reasoning_effort,
    )
    strategy_agent = StrategyAgent(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        reasoning_effort=settings.llm_reasoning_effort,
    )

    # Define Graph
    workflow = StateGraph(AlphaMinerState)

    # Add Nodes
    workflow.add_node("idea_agent", idea_agent)
    workflow.add_node("factor_agent", factor_agent)
    workflow.add_node("eval_agent", eval_agent)
    workflow.add_node("strategy_agent", strategy_agent)

    def strategy_eval_node(state: AlphaMinerState):
        from aiminer.core.evaluator_factory import build_evaluator, evaluation_config_from_mapping
        from aiminer.core.strategy import StrategyBacktester, StrategyConfig, selection_score

        candidates = state.get("strategy_candidates") or []
        if not candidates:
            return _merge_strategy_update_into_best_snapshot(
                state, {"strategy_results": [], "strategy_failure_reason": "no_candidates"}
            )

        expression = state.get("code_expression")
        if not expression:
            return _merge_strategy_update_into_best_snapshot(
                state,
                {"strategy_results": [], "strategy_failure_reason": "missing_expression"},
            )

        try:
            evaluator = build_evaluator(
                factor_expressions=[expression],
                config=evaluation_config_from_mapping(
                    {
                        "data_backend": state.get("data_backend", state.get("evaluation_mode", "ricequant")),
                        "evaluation_engine": state.get("evaluation_engine", "polars"),
                        "market_mode": state.get("market_mode", "single"),
                        "market_profile": state.get("market_profile", "cn_stock"),
                        "market_profiles": state.get("market_profiles"),
                        "local_data_path": state.get("local_data_path"),
                        "local_data_layout": state.get("local_data_layout", "auto"),
                        "market_start": state.get("market_analysis_start_date"),
                        "market_end": state.get("market_analysis_end_date"),
                    }
                ),
                test_start_date=state.get("market_analysis_start_date"),
                test_end_date=state.get("market_analysis_end_date"),
                daily_normalize=True,
            )
            evaluator.fetch_data()
            evaluator.compute_factors()
            signal_series = evaluator.factor_data.iloc[:, 0]
            label_series = evaluator.label_data["label"]
            # Align on the union of (date, ticker) pairs so unstack() yields
            # matching shapes regardless of per-source coverage gaps.
            common_idx = signal_series.index.union(label_series.index)
            signal_df = signal_series.reindex(common_idx).unstack().sort_index().sort_index(axis=1)
            label_df = label_series.reindex(common_idx).unstack().sort_index().sort_index(axis=1)
            label_df = label_df.reindex(index=signal_df.index, columns=signal_df.columns)
        except Exception as exc:
            logger.warning(f"[StrategyEval] Failed to prepare signal/label panels: {exc}")
            return _merge_strategy_update_into_best_snapshot(
                state,
                {
                    "strategy_results": [],
                    "strategy_failure_reason": "panel_construction_failed",
                    "messages": [f"[StrategyEval] Skipped strategy stage: {exc}"],
                },
            )
        if signal_df.empty or label_df.empty:
            return _merge_strategy_update_into_best_snapshot(
                state, {"strategy_results": [], "strategy_failure_reason": "empty_panels"}
            )

        factor_ic = float((state.get("backtest_metrics") or {}).get("information_coefficient", 0.0) or 0.0)
        results = []
        for idx, candidate in enumerate(candidates, start=1):
            cfg = candidate.get("strategy_config") or {}
            try:
                refinement_round = int(state.get("strategy_refinement_round", 0))
                backtester = StrategyBacktester(StrategyConfig.model_validate(cfg))
                # Refinement rounds get walk-forward to expose lucky-window
                # overfits before the critic asks for another lap.
                if refinement_round >= 1:
                    result = backtester.run_walk_forward(signal_df, label_df)
                else:
                    result = backtester.run(signal_df, label_df)
                metrics = result["metrics"]
                wf_aggregate = (result.get("walk_forward") or {}).get("aggregate")
                score = selection_score(metrics, factor_ic, walk_forward=wf_aggregate)
                payload = {
                    "strategy_id": f"{state.get('agent_id') or 'agent'}_r{refinement_round}_cand_{idx}",
                    "run_type": "strategy_backtest",
                    "status": "ok",
                    "candidate_rank": idx,
                    "is_primary": False,
                    "expression": expression,
                    "strategy_config": cfg,
                    "metrics": metrics,
                    "period_metrics": result.get("period_metrics", {}),
                    "walk_forward": result.get("walk_forward", {}),
                    "refinement_round": refinement_round,
                    "daily_returns": result["daily_returns"],
                    "positions": result["positions"],
                    "trade_stats": result["trade_stats"],
                    "market": cfg.get("market"),
                    "engine": cfg.get("engine"),
                    "label": cfg.get("label"),
                    "selection_score": score,
                    "rationale": candidate.get("rationale"),
                    "template_name": candidate.get("template_name"),
                    "chart_paths": {},
                    "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "data_backend": state.get("data_backend"),
                    "market_profile": state.get("market_profile"),
                    "market_mode": state.get("market_mode"),
                }
                results.append(payload)
            except Exception as exc:
                logger.warning(f"[StrategyEval] Candidate {idx} failed: {exc}")
        # Carry the previous round's best into the comparison pool so refinement
        # rounds only "win" when they strictly beat the incumbent.
        prior_best = state.get("best_strategy_result") if int(state.get("strategy_refinement_round", 0)) > 0 else None
        comparison_pool = list(results)
        if prior_best:
            comparison_pool.append(prior_best)

        if not comparison_pool:
            return _merge_strategy_update_into_best_snapshot(
                state,
                {
                    "strategy_results": [],
                    "strategy_failure_reason": "all_candidates_failed",
                },
            )
        best = max(comparison_pool, key=lambda item: item.get("selection_score", float("-inf")))
        best["is_primary"] = True
        return _merge_strategy_update_into_best_snapshot(state, {
            "strategy_results": results,
            "best_strategy_result": best,
            "best_strategy_config": best.get("strategy_config", {}),
            "best_strategy_metrics": best.get("metrics", {}),
            "best_strategy_id": best.get("strategy_id"),
            "strategy_daily_returns": best.get("daily_returns", {}),
            "selection_score": float(best.get("selection_score", 0.0) or 0.0),
            "strategy_failure_reason": None,
            "messages": [f"[StrategyEval] Selected {best.get('strategy_id')} score={best.get('selection_score', 0.0):.4f}"],
        })

    workflow.add_node("strategy_eval", strategy_eval_node)

    # Strategy critic node — Reflexion-style refinement loop.
    strategy_critic = StrategyCritic(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        reasoning_effort=settings.llm_reasoning_effort,
    )
    workflow.add_node("strategy_critic", strategy_critic)

    # Wiki update node
    def wiki_update_node(state: AlphaMinerState):
        if _state_has_evaluation_failure(state):
            logger.warning("[Workflow] Skipping Wiki update: evaluation failed.")
        else:
            logger.info("[Workflow] Updating LLM Wiki with results...")
            knowledge.update_wiki_after_eval(state)
        try:
            persist_agent_checkpoint(settings.db_path, state, settings=settings)
        except Exception as exc:
            logger.warning(f"[Workflow] Failed to persist agent checkpoint: {exc}")
        # Also refresh wiki context for next iteration retrieval
        query = f"Alpha factor ideas related to {state.get('role_prompt') or 'quantitative trading factors'}"
        return {"wiki_context": knowledge.wiki.retrieve(query)}

    workflow.add_node("wiki_update", wiki_update_node)

    # Increment state if looping
    workflow.add_node("increment", increment_iteration)

    # Set Entry Point
    workflow.set_entry_point("idea_agent")

    # Add Edges and Routing
    workflow.add_conditional_edges(
        "idea_agent", route_after_idea, {"factor_agent": "factor_agent", "end": END}
    )
    workflow.add_conditional_edges(
        "factor_agent", route_after_factor, {"eval_agent": "eval_agent", "end": END}
    )

    # After eval, go to wiki_update
    workflow.add_conditional_edges(
        "eval_agent", route_after_eval, {"strategy_agent": "strategy_agent", "wiki_update": "wiki_update", "end": END}
    )
    workflow.add_conditional_edges(
        "strategy_agent", route_after_strategy, {"strategy_eval": "strategy_eval", "wiki_update": "wiki_update", "end": END}
    )
    workflow.add_conditional_edges(
        "strategy_eval",
        route_after_strategy_eval,
        {"strategy_critic": "strategy_critic", "wiki_update": "wiki_update"},
    )
    workflow.add_conditional_edges(
        "strategy_critic",
        route_after_strategy_critic,
        {"strategy_eval": "strategy_eval", "wiki_update": "wiki_update"},
    )

    # After wiki_update, decide loop or end
    workflow.add_conditional_edges(
        "wiki_update", route_after_wiki, {"increment": "increment", "end": END}
    )

    # After incrementing, always go back to idea_agent
    workflow.add_edge("increment", "idea_agent")

    # Compile the graph
    app = workflow.compile()

    return app
