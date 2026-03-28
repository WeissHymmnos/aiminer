import os
import argparse
from dotenv import load_dotenv
from loguru import logger

# Load environment variables first, before initializing any agents or LangChain modules
load_dotenv()

from workflow.graph import build_workflow

def setup_logging():
    logger.add("logs/aiminer_{time}.log", rotation="10 MB", retention="10 days", level="DEBUG")

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Alpha Miner")
    parser.add_argument("--iterations", type=int, default=1, help="Number of factor mining iterations to run")
    args = parser.parse_args()

    setup_logging()
    logger.info(f"Initializing Multi-Agent AI Alpha Miner for {args.iterations} iteration(s)...")
    
    if not os.getenv("ClaudeCode_KEY"):
        logger.error("ClaudeCode_KEY is not set. Please ensure it's in your .env or environment.")
        return

    app = build_workflow()
    
    initial_state = {
        "iteration": 1,
        "max_iterations": args.iterations,
        "messages": ["[System] Starting Alpha Miner Workflow"]
    }
    
    logger.info("=== Starting LangGraph Execution ===")
    
    try:
        # Stream execution to see intermediate steps
        for output in app.stream(initial_state):
            for node_name, state_update in output.items():
                logger.info(f"--- Completed Node: {node_name} ---")
                
                # Check for errors in state update
                if "error" in state_update and state_update["error"]:
                    logger.error(f"Error in {node_name}: {state_update['error']}")
                    
        logger.info("=== Execution Complete ===")
        
    except Exception as e:
        logger.exception(f"Workflow execution failed: {e}")

if __name__ == "__main__":
    main()
