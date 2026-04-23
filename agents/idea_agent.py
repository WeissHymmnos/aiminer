from __future__ import annotations
from typing import Dict, Any
import re
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from app_workflow.state import AlphaMinerState
from core.hybrid_knowledge import HybridKnowledge
from core.llm import get_llm
from schemas.messages import HypothesisOutput


class IdeaAgent:
    """
    IdeaAgent is responsible for proposing market hypotheses.
    It uses HybridKnowledge (RAG + LLM Wiki) to fetch Qlib docs, Alpha/Academic Library,
    Market MetaData, and Past Experiences (structured as Wiki cards),
    then reasons over this context using a structured LLM call.
    """

    def __init__(
        self,
        knowledge: HybridKnowledge,
        provider: str = None,
        model: str = None,
        base_url: str = None,
        reasoning_effort: str = None,
    ):
        self.knowledge = knowledge
        self.llm = get_llm(
            temperature=0.7,
            provider=provider,
            model_name=model,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )

    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        """Remove markdown code block wrapper and sanitize control characters from JSON response."""
        text = text.strip()
        if text.startswith("```json"):
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        elif text.startswith("```"):
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        # Remove control characters except newlines and tabs that are part of JSON structure
        # Replace control characters within string values with spaces
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", " ", text)

        return text.strip()

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        iteration = state.get("iteration", 0)
        previous_improvements = state.get("suggested_improvements", "")
        previous_hypothesis = state.get("hypothesis_name", "")
        mode = state.get("evaluation_mode", "qlib")
        logger.info(f"[IdeaAgent] Starting iteration {iteration}")

        role_prompt = state.get(
            "role_prompt",
            "You are an elite quantitative researcher designing alpha factors for a high-frequency or statistical arbitrage fund.",
        )

        # 1. Hybrid Knowledge Retrieval: Retrieve context dynamically based on the role
        logger.info(
            f"[IdeaAgent] Retrieving hybrid context (RAG + Wiki) for role: {role_prompt[:30]}..."
        )
        base_query = f"Quantitative trading strategies, alpha factors, and past experiences (successes/failures) related to: {role_prompt}"
        combined_knowledge = self.knowledge.retrieve(base_query)

        # Retrieve Macro News specifically if dates are set (Skip if already in state)
        macro_context = state.get("macro_news_summary", "")
        if not macro_context and mode == "ricequant":
            logger.info("[IdeaAgent] Fetching macro events context...")
            macro_query = "What are the major macroeconomic news, central bank policies, and trade data?"
            macro_context = self.knowledge.rag.retrieve(macro_query, n_results=3)

        # Fetch Dynamic RiceQuant Market Insight if in ricequant mode (Skip if already in state)
        market_regime = state.get("market_regime_summary", "")
        data_backend = state.get("data_backend", mode)
        if not market_regime and data_backend in {"ricequant", "local"}:
            try:
                from core.evaluator_factory import build_evaluator, evaluation_config_from_mapping

                logger.info("[IdeaAgent] Fetching dynamic market regime analysis...")

                # Use params from state if available
                m_start = state.get("market_analysis_start_date")
                m_end = state.get("market_analysis_end_date")
                m_lookback = state.get("market_analysis_lookback_days", 60)

                # Default to 2018-2022 range for factor extraction context
                default_analysis_end = "2022-12-31"
                effective_end = m_end if m_end else default_analysis_end
                if not m_start and not m_end:
                    m_start = "2018-01-01"
                if m_start and m_start >= effective_end:
                    logger.warning(
                        f"[IdeaAgent] market_analysis_start_date ({m_start}) >= end ({effective_end}), skipping regime fetch."
                    )
                    raise ValueError(
                        f"Invalid date range: start={m_start} >= end={effective_end}"
                    )

                evaluator = build_evaluator(
                    factor_expressions=[],
                    config=evaluation_config_from_mapping(
                        {
                            "data_backend": data_backend,
                            "evaluation_mode": mode,
                            "evaluation_engine": state.get("evaluation_engine", "pandas"),
                            "market_mode": state.get("market_mode", "single"),
                            "market_profile": state.get("market_profile", "cn_stock"),
                            "market_profiles": state.get("market_profiles"),
                            "local_data_path": state.get("local_data_path"),
                            "local_data_layout": state.get("local_data_layout", "auto"),
                            "market_start": m_start,
                            "market_end": effective_end,
                        }
                    ),
                    test_end_date=effective_end,
                )
                market_regime = evaluator.get_market_regime(
                    start_date=m_start, end_date=m_end, lookback_days=m_lookback
                )
                logger.info(
                    f"[IdeaAgent] Injected RiceQuant Market Regime into context (Lookback: {m_lookback}d)."
                )
            except Exception as e:
                logger.warning(f"[IdeaAgent] Failed to fetch market regime: {e}")
                market_regime = "[市场数据暂时不可用，请基于通用量化逻辑生成假说]"

        # Combine static knowledge, macro news, and dynamic insight
        combined_context = (
            f"{combined_knowledge}\n\n"
            f"--- MACROECONOMIC NEWS & EVENTS ---\n{macro_context}\n\n"
            f"{market_regime}"
        )

        # Truncate context to save tokens (approx 6000 chars total for hybrid)
        if len(combined_context) > 6000:
            combined_context = combined_context[:6000] + "... [Truncated]"

        # 2. Reason Module: Formulate hypothesis
        system_msg = (
            f"{role_prompt}\n"
            "Use the provided HYBRID KNOWLEDGE (RAG + LLM WIKI) to inspire a novel hypothesis.\n"
            "IMPORTANT CROSS-AGENT LEARNING: The LLM WIKI contains structured 'Factor Cards' of past experiments. Learn from both your own past failures and the failures of other expert agents. Do not repeat failed logic or use identical mathematical structures that previously failed.\n\n"
            "IMPORTANT: Pay close attention to the MACRO NEWS and MARKET ANALYSIS provided.\n"
            "1. Macro News: Use central bank signals, trade data, or inflation trends to justify the economic rationale.\n"
            "2. Market Analysis: Tailor your hypothesis to the current regime (e.g. High Volatility, Bearish).\n\n"
            "SIGNAL QUALITY REQUIREMENT: Your hypothesis MUST produce a CONTINUOUS signal that varies smoothly across the entire cross-section of stocks. "
            "Avoid binary (0/1) or threshold-based ideas that assign the same value to most stocks. "
            "The best alpha factors rank ALL stocks along a continuous spectrum (e.g., momentum score, volatility ratio, mean-reversion magnitude), not just flag a few.\n\n"
            "You must respond with valid JSON matching this schema:\n"
            "{{\n"
            '  "hypothesis_name": "string",\n'
            '  "hypothesis_description": "string",\n'
            '  "rationale": "string"\n'
            "}}\n\n"
            "Context:\n{context}"
        )
        if previous_improvements and iteration > 1:
            system_msg += f"\n\nFeedback from previous iteration (DO NOT IGNORE THIS): {previous_improvements}"

        user_prompt = f"Propose a new factor hypothesis for iteration {iteration}.\n"
        if iteration > 1 and previous_improvements:
            user_prompt += (
                f"\nCRITICAL FEEDBACK FROM ITERATION {iteration - 1}:\n"
                f"Your previous hypothesis was '{previous_hypothesis}'.\n"
                f"The backtest evaluation provided the following required improvements:\n"
                f"=== FEEDBACK ===\n{previous_improvements}\n================\n\n"
                "You MUST explicitly incorporate this feedback into your new hypothesis. "
                "Do NOT propose the same failed logic. Modify the core mathematical approach or economic rationale as suggested.\n\n"
            )
        user_prompt += (
            "Explain the economic rationale clearly.\n"
            "Return ONLY valid JSON matching the exact schema, no markdown code blocks, no extra text."
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_msg), ("user", user_prompt)]
        )

        chain = prompt | self.llm

        try:
            logger.info(
                f"[IdeaAgent] LLM ({self.llm.model_name}) is thinking deeply about hypothesis for iteration {iteration}..."
            )
            raw_response = chain.invoke(
                {"context": combined_context, "iteration": iteration}
            )
            cleaned_json = self._strip_markdown_json(raw_response.content)
            result = HypothesisOutput.model_validate_json(cleaned_json)

            logger.info(f"[IdeaAgent] Hypothesis Generated: {result.hypothesis_name}")

            return {
                "rag_context": combined_knowledge,  # Now contains both
                "macro_news_summary": macro_context,
                "market_regime_summary": market_regime,
                "hypothesis_name": result.hypothesis_name,
                "hypothesis_description": result.hypothesis_description,
                "rationale": result.rationale,
                "messages": [
                    f"[IdeaAgent] Proposed: {result.hypothesis_name} - {result.hypothesis_description}"
                ],
            }
        except Exception as e:
            logger.error(f"[IdeaAgent] Failed to generate hypothesis: {e}")
            try:
                logger.debug(
                    f"[IdeaAgent] Raw LLM response that failed parsing:\n{raw_response.content}"
                )
            except NameError:
                pass  # raw_response not yet assigned (e.g. LLM call itself failed)
            return {"error": str(e), "messages": [f"[IdeaAgent] Error: {e}"]}
