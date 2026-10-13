"""Comprehensive Robustness Test for AI Alpha Miner with Muse Spark 1.3 Contributor High.

Connects through local CPAproxy (http://127.0.0.1:8317/v1) to test:
1. CPAproxy upstream routing and Responses API bridge stability.
2. IdeaAgent hypothesis formulation and JSON output resilience under high reasoning effort.
3. FactorAgent formalization and Qlib code expression AST validation.
4. Expression dry-run execution on quantitative data matrix.
5. Multi-round adaptive feedback reasoning with simulated backtest results.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict

# Ensure src is in python path
sys.path.insert(0, os.path.abspath("src"))

# Set auth and base_url for CPAproxy
os.environ["OPENAI_API_KEY"] = "huahongrui"
os.environ["OpenAI_KEY"] = "huahongrui"
os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8317/v1"
os.environ["AIMINER_DISABLE_CHROMA"] = "1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

from loguru import logger

from aiminer.agents.factor_agent import FactorAgent
from aiminer.agents.idea_agent import IdeaAgent
from aiminer.app_workflow.state import AlphaMinerState
from aiminer.core.alphaeval.rq_eval import RiceQuantEval
from aiminer.core.hybrid_knowledge import HybridKnowledge
from aiminer.core.llm import get_llm
from aiminer.core.rag import RAGModule
from aiminer.core.wiki import LLMWiki


def test_1_llm_connectivity_and_reasoning() -> Dict[str, Any]:
    logger.info(
        "=== STEP 1: Direct LLM Connectivity & High Reasoning Effort ==="
    )
    from langchain_core.messages import HumanMessage

    t0 = time.time()
    llm = get_llm(
        provider="openai",
        model_name="muse-spark-1.3-contributor-high",
        base_url="http://127.0.0.1:8317/v1",
        temperature=0.2,
    )
    prompt = (
        "In quantitative finance, explain in 2 concise sentences why "
        "volatility-standardized momentum outperforms raw price momentum."
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    elapsed = time.time() - t0

    logger.info(f"LLM Response received in {elapsed:.2f}s:")
    logger.info(f"Content: {resp.content.strip()}")

    assert len(resp.content.strip()) > 20, "Response is too short or empty"
    return {"elapsed": elapsed, "response": resp.content.strip()}


def test_2_idea_agent_robustness() -> Dict[str, Any]:
    logger.info(
        "=== STEP 2: IdeaAgent Hypothesis Generation & JSON Parsing ==="
    )
    knowledge = HybridKnowledge(
        llm_provider="openai",
        llm_model="muse-spark-1.3-contributor-high",
        llm_base_url="http://127.0.0.1:8317/v1",
    )

    agent = IdeaAgent(
        knowledge=knowledge,
        provider="openai",
        model="muse-spark-1.3-contributor-high",
        base_url="http://127.0.0.1:8317/v1",
    )

    state: AlphaMinerState = {
        "iteration": 1,
        "evaluation_mode": "ricequant",
        "data_backend": "ricequant",
        "role_prompt": (
            "You are a Senior Quantitative Alpha Researcher specializing in "
            "cross-sectional equity momentum and reversal anomalies."
        ),
        "suggested_improvements": "",
        "hypothesis_name": "",
        "market_regime_summary": "High market volatility with cyclical factor rotation.",
    }

    t0 = time.time()
    result = agent(state)
    elapsed = time.time() - t0

    logger.info(f"IdeaAgent completed in {elapsed:.2f}s")
    logger.info(f"Hypothesis Name: {result.get('hypothesis_name')}")
    logger.info(f"Description: {result.get('hypothesis_description')}")
    logger.info(f"Rationale: {result.get('rationale')}")

    assert result.get("hypothesis_name"), "Missing hypothesis_name"
    assert result.get("hypothesis_description"), (
        "Missing hypothesis_description"
    )
    assert result.get("rationale"), "Missing rationale"

    return {
        "elapsed": elapsed,
        "hypothesis_name": result["hypothesis_name"],
        "hypothesis_description": result["hypothesis_description"],
        "rationale": result["rationale"],
    }


def test_3_factor_agent_formalization_and_ast(
    hypothesis: Dict[str, Any],
) -> Dict[str, Any]:
    logger.info("=== STEP 3: FactorAgent Formalization & AST Validation ===")
    agent = FactorAgent(
        provider="openai",
        model="muse-spark-1.3-contributor-high",
        base_url="http://127.0.0.1:8317/v1",
    )

    state: AlphaMinerState = {
        "iteration": 1,
        "evaluation_mode": "ricequant",
        "hypothesis_name": hypothesis["hypothesis_name"],
        "hypothesis_description": hypothesis["hypothesis_description"],
        "rationale": hypothesis["rationale"],
        "role_prompt": "You are a quantitative developer writing strict Qlib alpha expressions.",
    }

    t0 = time.time()
    result = agent(state)
    elapsed = time.time() - t0

    logger.info(f"FactorAgent completed in {elapsed:.2f}s")
    logger.info(f"Math Formula: {result.get('math_formula')}")
    logger.info(f"Code Expression: {result.get('code_expression')}")
    logger.info(f"Is Valid Syntax: {result.get('is_valid_syntax')}")

    assert result.get("code_expression"), "Missing code_expression"
    assert result.get("is_valid_syntax") is True, (
        f"Syntax invalid: {result.get('syntax_error')}"
    )

    return {
        "elapsed": elapsed,
        "math_formula": result.get("math_formula"),
        "code_expression": result.get("code_expression"),
        "is_valid_syntax": result.get("is_valid_syntax"),
    }


def test_4_expression_dry_run_execution(code_expression: str) -> None:
    logger.info("=== STEP 4: Expression Matrix Dry-Run Validation ===")
    logger.info(f"Validating expression: {code_expression}")

    is_valid, msg = RiceQuantEval.dry_run(code_expression)
    logger.info(f"Dry run result: valid={is_valid}, msg={msg}")
    assert is_valid is True, f"Dry-run execution failed: {msg}"


def test_5_multi_round_feedback_adaptation() -> None:
    logger.info("=== STEP 5: Multi-Round Iterative Feedback Reasoning ===")
    knowledge = HybridKnowledge(
        llm_provider="openai",
        llm_model="muse-spark-1.3-contributor-high",
        llm_base_url="http://127.0.0.1:8317/v1",
    )

    idea_agent = IdeaAgent(
        knowledge=knowledge,
        provider="openai",
        model="muse-spark-1.3-contributor-high",
        base_url="http://127.0.0.1:8317/v1",
    )

    factor_agent = FactorAgent(
        provider="openai",
        model="muse-spark-1.3-contributor-high",
        base_url="http://127.0.0.1:8317/v1",
    )

    state: AlphaMinerState = {
        "iteration": 2,
        "evaluation_mode": "ricequant",
        "data_backend": "ricequant",
        "role_prompt": "You are a quantitative researcher.",
        "previous_hypothesis": "ShortTermPriceReversal",
        "suggested_improvements": (
            "CRITICAL BACKTEST FAILURE: The factor exhibited strong negative IC (-0.052) "
            "and an excessively high daily turnover (88%). "
            "REQUIRED FIX: 1) Invert the factor direction (use negative or inverse ranking). "
            "2) Apply a 10-day rolling Mean or EMA filter to reduce noise and turnover."
        ),
        "market_regime_summary": "Sideways market with heavy intraday noise.",
    }

    logger.info("Querying IdeaAgent with backtest critique...")
    idea_result = idea_agent(state)
    logger.info(f"Iter 2 Hypothesis: {idea_result.get('hypothesis_name')}")
    logger.info(f"Iter 2 Rationale: {idea_result.get('rationale')}")

    state["hypothesis_name"] = idea_result["hypothesis_name"]
    state["hypothesis_description"] = idea_result["hypothesis_description"]
    state["rationale"] = idea_result["rationale"]

    logger.info("Querying FactorAgent for updated implementation...")
    factor_result = factor_agent(state)
    expr = factor_result.get("code_expression", "")
    logger.info(f"Iter 2 Formula: {factor_result.get('math_formula')}")
    logger.info(f"Iter 2 Code Expression: {expr}")
    logger.info(f"Iter 2 Valid Syntax: {factor_result.get('is_valid_syntax')}")

    assert factor_result.get("is_valid_syntax") is True, (
        f"Iter 2 syntax error: {factor_result.get('syntax_error')}"
    )
    is_valid, msg = RiceQuantEval.dry_run(expr)
    assert is_valid is True, f"Iter 2 dry run failed: {msg}"
    logger.info("Iter 2 factor successfully dry-run validated!")


def main():
    logger.info(
        "Starting AI Alpha Miner Robustness Test with Muse Spark 1.3 Contributor High..."
    )
    t_start = time.time()

    # Step 1: Connectivity & Reasoning
    step1 = test_1_llm_connectivity_and_reasoning()

    # Step 2: IdeaAgent
    hypothesis = test_2_idea_agent_robustness()

    # Step 3: FactorAgent
    factor = test_3_factor_agent_formalization_and_ast(hypothesis)

    # Step 4: Dry-Run
    test_4_expression_dry_run_execution(factor["code_expression"])

    # Step 5: Iterative Feedback
    test_5_multi_round_feedback_adaptation()

    total_time = time.time() - t_start
    logger.info(f"ALL ROBUSTNESS TESTS PASSED in {total_time:.2f}s!")


if __name__ == "__main__":
    main()
