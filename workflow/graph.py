from __future__ import annotations
from langgraph.graph import StateGraph, END
from loguru import logger
from workflow.state import AlphaMinerState
from agents.idea_agent import IdeaAgent
from agents.factor_agent import FactorAgent
from agents.eval_agent import EvalAgent
from core.hybrid_knowledge import HybridKnowledge


# Routing Functions
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
    # Route after eval: move to wiki_update then decide loop or end.
    if state.get("error"):
        return "end"
    return "wiki_update"


def route_after_wiki(state: AlphaMinerState) -> str:
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 1)

    metrics = state.get("backtest_metrics", {})
    current_ic = metrics.get("information_coefficient", 0.0)
    is_simulated = state.get("is_simulated", False)

    # 1. Early Stopping: High IC achieved — only on real (non-simulated) data
    is_simulated = state.get("is_simulated", False)
    if current_ic >= 0.05 and not is_simulated:
        logger.success(f"[Early Stop] Exceptional IC reached: {current_ic:.4f}")
        return "end"
    if current_ic >= 0.05 and is_simulated:
        logger.warning(
            f"[Router] IC={current_ic:.4f} looks exceptional but metrics are SIMULATED — "
            "ignoring early stop trigger and continuing."
        )

    # 2. Early Stopping: Patience exhausted
    patience = state.get("patience_counter", 0)
    if patience >= 4:
        logger.info("[Early Stop] No IC improvement for 4 consecutive iterations.")
        return "end"

    if iteration < max_iterations:
        return "increment"
    return "end"


def increment_iteration(state: AlphaMinerState):
    return {
        "iteration": state.get("iteration", 1) + 1,
        "best_ic": state.get("best_ic", -999.0),
        "best_code_expression": state.get(
            "best_code_expression", state.get("code_expression")
        ),
        "patience_counter": state.get("patience_counter", 0),
        "error": None,
        "is_valid_syntax": True,
        # Clear per-iteration agent outputs to prevent state pollution
        "hypothesis_name": None,
        "hypothesis_description": None,
        "rationale": None,
        "code_expression": None,
        "math_formula": None,
        "variables_defined": None,
        "backtest_metrics": None,
        "review_summary": None,
        "is_effective": None,
        "is_simulated": False,
        "suggested_improvements": None,
    }


def build_workflow(
    rebuild_rag: bool = False,
    llm_provider: str = None,
    llm_model: str = None,
    embedding_provider: str = None,
    use_gpu: bool = False,
):
    # Initialize shared knowledge base
    knowledge = HybridKnowledge(
        rebuild_rag=rebuild_rag,
        embedding_provider=embedding_provider,
        use_gpu=use_gpu,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

    # Initialize agents
    idea_agent = IdeaAgent(knowledge, provider=llm_provider, model=llm_model)
    factor_agent = FactorAgent(provider=llm_provider, model=llm_model)
    eval_agent = EvalAgent(knowledge, provider=llm_provider, model=llm_model)

    # Define Graph
    workflow = StateGraph(AlphaMinerState)

    # Add Nodes
    workflow.add_node("idea_agent", idea_agent)
    workflow.add_node("factor_agent", factor_agent)
    workflow.add_node("eval_agent", eval_agent)

    # Wiki update node
    def wiki_update_node(state: AlphaMinerState):
        logger.info("[Workflow] Updating LLM Wiki with results...")
        knowledge.update_wiki_after_eval(state)
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
        "eval_agent", route_after_eval, {"wiki_update": "wiki_update", "end": END}
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
