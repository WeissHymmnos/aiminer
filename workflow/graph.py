from langgraph.graph import StateGraph, END
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
    if state.get("error") or not state.get("is_valid_syntax", True):
        # We could route back to IdeaAgent here, but for simplicity we'll end or skip to eval
        # In a highly robust system, if syntax is invalid, route back to factor_agent to retry
        return "end" if state.get("error") else "eval_agent"

def route_after_eval(state: AlphaMinerState) -> str:
    # Check if we should iterate
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 1)
    
    if iteration < max_iterations:
        return "idea_agent"
    return "end"

def increment_iteration(state: AlphaMinerState):
    return {"iteration": state.get("iteration", 1) + 1, "error": None}

def build_workflow():
    # Initialize shared resources
    rag_module = RAGModule()
    
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
    
    workflow.add_edge("eval_agent", "increment")
    
    workflow.add_conditional_edges(
        "increment",
        route_after_eval,
        {
            "idea_agent": "idea_agent",
            "end": END
        }
    )

    # Compile the graph
    app = workflow.compile()
    
    return app
