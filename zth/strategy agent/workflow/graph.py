from langgraph.graph import StateGraph, END
from loguru import logger
from workflow.state import AlphaMinerState
from agents.idea_agent import IdeaAgent
from agents.factor_agent import FactorAgent
from agents.eval_agent import EvalAgent
from core.rag import RAGModule

# Routing Functions
def route_after_idea(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "end"
    return "factor_agent"

def route_after_factor(state: AlphaMinerState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("is_valid_syntax", True):
        logger.warning("[Router] Invalid syntax detected — skipping to eval with caveat.")
    return "eval_agent"

def route_after_eval(state: AlphaMinerState) -> str:
    # Route after eval: check if we should loop for another iteration.
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 1)
    
    metrics = state.get("backtest_metrics", {})
    current_ic = metrics.get("information_coefficient", 0.0)
    
    # 1. Early Stopping: High IC achieved
    if current_ic >= 0.05:
        logger.success(f"[Early Stop] Exceptional IC reached: {current_ic:.4f}")
        return "end"
        
    # 2. Early Stopping: Patience exhausted
    patience = state.get("patience_counter", 0)
    if patience >= 3:
        logger.info(f"[Early Stop] No IC improvement for 3 consecutive iterations.")
        return "end"
    
    if iteration < max_iterations:
        return "increment"
    return "end"

def increment_iteration(state: AlphaMinerState):
    return {
        "iteration": state.get("iteration", 1) + 1,
        "error": None,
        "is_valid_syntax": True,  # Reset for next iteration
    }

def build_workflow(
    rebuild_rag: bool = False,
    llm_provider: str = None,
    llm_model: str = None,
    embedding_provider: str = None,
    use_gpu: bool = False
):
    # Initialize shared resources
    rag_module = RAGModule(rebuild=rebuild_rag, embedding_provider=embedding_provider, use_gpu=use_gpu)
    
    # Initialize agents
    idea_agent = IdeaAgent(rag_module, provider=llm_provider, model=llm_model)
    factor_agent = FactorAgent(provider=llm_provider, model=llm_model)
    eval_agent = EvalAgent(rag_module, provider=llm_provider, model=llm_model)

    # Define Graph
    workflow = StateGraph(AlphaMinerState)

    # Add Nodes
    workflow.add_node("idea_agent", idea_agent)
    workflow.add_node("factor_agent", factor_agent)
    workflow.add_node("eval_agent", eval_agent)
    
    # Increment state if looping
    workflow.add_node("increment", increment_iteration)

    # Set Entry Point
    workflow.set_entry_point("idea_agent")

    # Add Edges and Routing
    workflow.add_conditional_edges("idea_agent", route_after_idea, {"factor_agent": "factor_agent", "end": END})
    workflow.add_conditional_edges("factor_agent", route_after_factor, {"eval_agent": "eval_agent", "end": END})
    
    # After eval, decide loop or end
    workflow.add_conditional_edges(
        "eval_agent",
        route_after_eval,
        {
            "increment": "increment",
            "end": END
        }
    )
    
    # After incrementing, always go back to idea_agent
    workflow.add_edge("increment", "idea_agent")

    # Compile the graph
    app = workflow.compile()
    
    return app
