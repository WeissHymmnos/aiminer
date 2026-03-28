from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from workflow.state import AlphaMinerState
from core.rag import RAGModule
from core.llm import get_llm
from schemas.messages import HypothesisOutput

class IdeaAgent:
    \"\"\"
    IdeaAgent is responsible for proposing market hypotheses.
    It uses RAG to fetch Qlib docs, Alpha/Academic Library, Market MetaData, and Past Experiences,
    then reasons over this context using a structured LLM call.
    \"\"\"
    def __init__(self, rag_module: RAGModule):
        self.rag = rag_module
        self.llm = get_llm(temperature=0.7)
        self.structured_llm = self.llm.with_structured_output(HypothesisOutput)

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        iteration = state.get("iteration", 0)
        logger.info(f"[IdeaAgent] Starting iteration {iteration}")
        
        # 1. RAG Module: Retrieve context
        query = f"Generate a novel quantitative trading alpha factor hypothesis. Focus on robustness and high Information Coefficient (IC)."
        rag_context = self.rag.retrieve(query)
        logger.debug(f"[IdeaAgent] Retrieved Context Length: {len(rag_context)}")
        
        # 2. Reason Module: Formulate hypothesis
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an elite quantitative researcher designing alpha factors for a high-frequency or statistical arbitrage fund. "
                       "Use the provided context to inspire a novel hypothesis. Do not repeat failed past experiences.\\n\\n"
                       "Context:\\n{context}"),
            ("user", "Propose a new factor hypothesis for iteration {iteration}. "
                     "Explain the economic rationale clearly.")
        ])
        
        chain = prompt | self.structured_llm
        
        try:
            result: HypothesisOutput = chain.invoke({
                "context": rag_context,
                "iteration": iteration
            })
            
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
