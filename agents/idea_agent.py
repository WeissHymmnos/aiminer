from typing import Dict, Any
import re
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from workflow.state import AlphaMinerState
from core.rag import RAGModule
from core.llm import get_llm
from schemas.messages import HypothesisOutput

class IdeaAgent:
    """
    IdeaAgent is responsible for proposing market hypotheses.
    It uses RAG to fetch Qlib docs, Alpha/Academic Library, Market MetaData, and Past Experiences,
    then reasons over this context using a structured LLM call.
    """
    def __init__(self, rag_module: RAGModule, provider: str = None, model: str = None):
        self.rag = rag_module
        self.llm = get_llm(temperature=0.7, provider=provider, model_name=model)
    
    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        """Remove markdown code block wrapper and sanitize control characters from JSON response."""
        text = text.strip()
        if text.startswith("```json"):
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        elif text.startswith("```"):
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        
        # Remove control characters except newlines and tabs that are part of JSON structure
        # Replace control characters within string values with spaces
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', ' ', text)
        
        return text.strip()

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        iteration = state.get("iteration", 0)
        previous_improvements = state.get("suggested_improvements", "")
        previous_hypothesis = state.get("hypothesis_name", "")
        mode = state.get("evaluation_mode", "qlib")
        logger.info(f"[IdeaAgent] Starting iteration {iteration}")
        
        # 1. RAG Module: Retrieve context
        base_query = "Generate a novel quantitative trading alpha factor hypothesis."
        rag_context = self.rag.retrieve(base_query)
        
        # Retrieve Macro News specifically if dates are set (Skip if already in state)
        macro_context = state.get("macro_news_summary", "")
        if not macro_context and mode == "ricequant":
             macro_query = "What are the major macroeconomic news, central bank policies, and trade data?"
             macro_context = self.rag.retrieve(macro_query, n_results=3)
        
        # Fetch Dynamic RiceQuant Market Insight if in ricequant mode (Skip if already in state)
        market_regime = state.get("market_regime_summary", "")
        if not market_regime and mode == "ricequant":
            try:
                from core.alphaeval.rq_eval import RiceQuantEval
                
                # Use params from state if available
                m_start = state.get("market_analysis_start_date")
                m_end = state.get("market_analysis_end_date")
                m_lookback = state.get("market_analysis_lookback_days", 60) # Default to 60 for better stats
                
                rq_eval = RiceQuantEval(
                    factor_expressions=[], 
                    test_end_date=m_end if m_end else "2020-10-31"
                )
                market_regime = rq_eval.get_market_regime(
                    start_date=m_start,
                    end_date=m_end,
                    lookback_days=m_lookback
                )
                logger.info(f"[IdeaAgent] Injected RiceQuant Market Regime into context (Lookback: {m_lookback}d).")
            except Exception as e:
                logger.warning(f"[IdeaAgent] Failed to fetch market regime: {e}")
                pass
        
        # Combine static knowledge, macro news, and dynamic insight
        combined_context = (
            f"--- HISTORICAL KNOWLEDGE & THEORY ---\n{rag_context}\n\n"
            f"--- MACROECONOMIC NEWS & EVENTS ---\n{macro_context}\n\n"
            f"{market_regime}"
        )
        
        # Truncate context to save tokens (approx 4000 chars total)
        if len(combined_context) > 4000:
            combined_context = combined_context[:4000] + "... [Truncated]"
        
        # 2. Reason Module: Formulate hypothesis
        role_prompt = state.get("role_prompt", "You are an elite quantitative researcher designing alpha factors for a high-frequency or statistical arbitrage fund.")
        system_msg = (f"{role_prompt}\n"
                      "Use the provided context to inspire a novel hypothesis. Do not repeat failed past experiences.\n\n"
                      "IMPORTANT: Pay close attention to the MACRO NEWS and MARKET ANALYSIS provided.\n"
                      "1. Macro News: Use central bank signals, trade data, or inflation trends to justify the economic rationale.\n"
                      "2. Market Analysis: Tailor your hypothesis to the current regime (e.g. High Volatility, Bearish).\n\n"
                      "You must respond with valid JSON matching this schema:\n"
                      "{{\n"
                      '  "hypothesis_name": "string",\n'
                      '  "hypothesis_description": "string",\n'
                      '  "rationale": "string"\n'
                      "}}\n\n"
                      "Context:\n{context}")
        if previous_improvements and iteration > 1:
            system_msg += f"\n\nFeedback from previous iteration: {previous_improvements}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("user", "Propose a new factor hypothesis for iteration {iteration}. "
                     "Explain the economic rationale clearly. "
                     "Return ONLY valid JSON, no markdown code blocks, no extra text.")
        ])
        
        chain = prompt | self.llm
        
        try:
            raw_response = chain.invoke({
                "context": combined_context,
                "iteration": iteration
            })
            cleaned_json = self._strip_markdown_json(raw_response.content)
            result = HypothesisOutput.model_validate_json(cleaned_json)
            
            logger.info(f"[IdeaAgent] Hypothesis Generated: {result.hypothesis_name}")
            
            return {
                "rag_context": rag_context,
                "macro_news_summary": macro_context,
                "market_regime_summary": market_regime,
                "hypothesis_name": result.hypothesis_name,
                "hypothesis_description": result.hypothesis_description,
                "rationale": result.rationale,
                "messages": [f"[IdeaAgent] Proposed: {result.hypothesis_name} - {result.hypothesis_description}"]
            }
        except Exception as e:
            logger.error(f"[IdeaAgent] Failed to generate hypothesis: {e}")
            return {
                "error": str(e),
                "messages": [f"[IdeaAgent] Error: {e}"]
            }
