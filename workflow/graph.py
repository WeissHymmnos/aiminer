from langgraph.graph import StateGraph, END
from loguru import logger
from workflow.state import AlphaMinerState
from agents.idea_agent import IdeaAgent
from agents.factor_agent import FactorAgent
from agents.eval_agent import EvalAgent
from core.rag import RAGModule

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
    """Route after eval: check if we should loop for another iteration.
    
    Note: increment runs *after* this routing, so we compare against
    max_iterations using the current (not yet incremented) iteration.
    """
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 1)
    
    if iteration < max_iterations:
        return "increment"
    return "end"

def increment_iteration(state: AlphaMinerState):
    """Increment iteration counter and clear transient error state."""
    return {
        "iteration": state.get("iteration", 1) + 1,
        "error": None,
        "is_valid_syntax": True,  # Reset for next iteration
    }

def build_workflow(rebuild_rag: bool = False):
    # Initialize shared resources
    rag_module = RAGModule(rebuild=rebuild_rag)
    
    # Initialize agents
    idea_agent = IdeaAgent(rag_module)
    factor_agent = FactorAgent()
    eval_agent = EvalAgent(rag_module)

    # Define Graph
    workflow = StateGraph(AlphaMinerState)

    # Add Nodes
    workflow.add_node("idea_agent", idea_agent)
    workflow.add_node("factor_agent", factor_agent)
    workflow.add_node("eval_agent", eval_agent)
    
    # Optional: A node just to increment state if looping
    workflow.add_node("increment", increment_iteration)

    # Set Entry Point
    workflow.set_entry_point("idea_agent")

    # Add Edges and Routing
    workflow.add_conditional_edges("idea_agent", route_after_idea, {"factor_agent": "factor_agent", "end": END})
    workflow.add_conditional_edges("factor_agent", route_after_factor, {"eval_agent": "eval_agent", "end": END})
    
    # After eval, decide whether to loop or end
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
