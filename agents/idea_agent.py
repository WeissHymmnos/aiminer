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
    def __init__(self, rag_module: RAGModule):
        self.rag = rag_module
        self.llm = get_llm(temperature=0.7)
    
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
        logger.info(f"[IdeaAgent] Starting iteration {iteration}")
        
        # 1. RAG Module: Retrieve context — incorporate feedback from prior iteration
        base_query = "Generate a novel quantitative trading alpha factor hypothesis. Focus on robustness and high Information Coefficient (IC)."
        if previous_improvements and iteration > 1:
            query = f"{base_query} Previous attempt '{previous_hypothesis}' had these suggestions: {previous_improvements}"
        else:
            query = base_query
        rag_context = self.rag.retrieve(query)
        logger.debug(f"[IdeaAgent] Retrieved Context Length: {len(rag_context)}")
        
        # 2. Reason Module: Formulate hypothesis
        system_msg = ("You are an elite quantitative researcher designing alpha factors for a high-frequency or statistical arbitrage fund. "
                      "Use the provided context to inspire a novel hypothesis. Do not repeat failed past experiences.\n\n"
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
                "context": rag_context,
                "iteration": iteration
            })
            cleaned_json = self._strip_markdown_json(raw_response.content)
            result = HypothesisOutput.model_validate_json(cleaned_json)
            
            logger.info(f"[IdeaAgent] Hypothesis Generated: {result.hypothesis_name}")
            
            return {
                "rag_context": rag_context,
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
