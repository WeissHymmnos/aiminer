import os
import sys
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Load environment variables first, before initializing any agents or LangChain modules
load_dotenv()

from workflow.graph import build_workflow

def setup_logging(verbose: bool = False):
    os.makedirs("logs", exist_ok=True)
    logger.add("logs/aiminer_{time}.log", rotation="10 MB", retention="10 days", level="DEBUG")
    if verbose:
        logger.add(sys.stderr, level="DEBUG")

def save_results(final_state: dict, output_file: str = "results/results.json"):
    """Save execution results to JSON file."""
    os.makedirs("results", exist_ok=True)
    
    result_entry = {
        "timestamp": datetime.now().isoformat(),
        "iteration": final_state.get("iteration"),
        "max_iterations": final_state.get("max_iterations"),
        "hypothesis_name": final_state.get("hypothesis_name"),
        "hypothesis_description": final_state.get("hypothesis_description"),
        "code_expression": final_state.get("code_expression"),
        "backtest_metrics": final_state.get("backtest_metrics", {}),
        "is_simulated": final_state.get("is_simulated", False),
        "is_effective": final_state.get("is_effective"),
        "review_summary": final_state.get("review_summary"),
        "suggested_improvements": final_state.get("suggested_improvements"),
        "error": final_state.get("error")
    }
    
    # Load existing results
    results = {"results": []}
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    
    # Append new result
    results["results"].append(result_entry)
    
    # Save back
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {output_file}")

def print_summary(final_state: dict):
    """Print a human-readable summary of the final workflow state."""
    print("\n" + "=" * 60)
    print("  ALPHA MINER — EXECUTION SUMMARY")
    print("=" * 60)
    
    iteration = final_state.get("iteration", "?")
    max_iter = final_state.get("max_iterations", "?")
    print(f"  Iterations completed: {iteration} / {max_iter}")
    
    if final_state.get("hypothesis_name"):
        print(f"\n  Last Hypothesis: {final_state['hypothesis_name']}")
    if final_state.get("hypothesis_description"):
        print(f"  Description: {final_state['hypothesis_description'][:120]}...")
    if final_state.get("code_expression"):
        print(f"  Expression: {final_state['code_expression'][:120]}")
    
    metrics = final_state.get("backtest_metrics", {})
    if metrics:
        simulated = final_state.get("is_simulated", False)
        print(f"\n  Backtest Metrics {'(SIMULATED)' if simulated else '(REAL)'}:")
        for k, v in metrics.items():
            print(f"    {k}: {v}")
    
    if final_state.get("is_effective") is not None:
        print(f"\n  Effective: {'✓ YES' if final_state['is_effective'] else '✗ NO'}")
    if final_state.get("review_summary"):
        print(f"  Review: {final_state['review_summary'][:200]}")
    if final_state.get("suggested_improvements"):
        print(f"  Improvements: {final_state['suggested_improvements'][:200]}")
    
    if final_state.get("error"):
        print(f"\n  ⚠ Last Error: {final_state['error']}")
    
    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Alpha Miner")
    parser.add_argument("--iterations", type=int, default=1, help="Number of factor mining iterations to run")
    parser.add_argument("--rebuild-rag", action="store_true", help="Force rebuild the RAG knowledge base from docs")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging to stderr")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger.info(f"Initializing Multi-Agent AI Alpha Miner for {args.iterations} iteration(s)...")
    
    if not os.getenv("ClaudeCode_KEY"):
        logger.error("ClaudeCode_KEY is not set. Please ensure it's in your .env or environment.")
        return

    app = build_workflow(rebuild_rag=args.rebuild_rag)
    
    initial_state = {
        "iteration": 1,
        "max_iterations": args.iterations,
        "messages": ["[System] Starting Alpha Miner Workflow"]
    }
    
    logger.info("=== Starting LangGraph Execution ===")
    
    final_state = initial_state
    try:
        # Stream execution to see intermediate steps
        for output in app.stream(initial_state):
            for node_name, state_update in output.items():
                logger.info(f"--- Completed Node: {node_name} ---")
                final_state.update(state_update)
                
                # Check for errors in state update
                if "error" in state_update and state_update["error"]:
                    logger.error(f"Error in {node_name}: {state_update['error']}")
                    
        logger.info("=== Execution Complete ===")
        save_results(final_state)
        print_summary(final_state)
        
    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user.")
        save_results(final_state)
        print_summary(final_state)
    except Exception as e:
        logger.exception(f"Workflow execution failed: {e}")
        save_results(final_state)
        print_summary(final_state)

if __name__ == "__main__":
    main()
