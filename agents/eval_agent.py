from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
import random
import hashlib
import re
from loguru import logger
from workflow.state import AlphaMinerState
from core.rag import RAGModule
from core.llm import get_llm
from schemas.messages import ReflexiveReviewOutput

class EvalAgent:
    """
    EvalAgent evaluates the factor/strategy effectiveness.
    Uses AlphaEval from GitHub for backtesting and evaluation, 
    along with a Reflexive Review module.
    Outputs experience to RAG.
    """
    def __init__(self, rag_module: RAGModule):
        self.rag = rag_module
        self.llm = get_llm(temperature=0.4)
    
    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        """Remove markdown code block wrapper from JSON response."""
        text = text.strip()
        if text.startswith("```json"):
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        elif text.startswith("```"):
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        return text.strip()

    def _execute_alphaeval_backtest(self, code: str) -> Dict[str, float]:
        """
        Uses AlphaEval framework to backtest and evaluate the generated formula.
        In a production environment, this requires Qlib data initialized.
        """
        logger.info(f"[EvalAgent] Executing AlphaEval for expression: {code}")
        
        try:
            from core.alphaeval.modeltester import AlphaEval
            
            # Use AlphaEval to run backtesting and factor evaluation
            evaluator = AlphaEval(
                factor_expressions=[code],
                weights=[1.0],  # Single factor weight
                train_start_date="2010-01-01",
                train_end_date="2016-12-31",
                test_start_date="2017-01-01",
                test_end_date="2020-10-31",
                daily_normalize=True
            )
            
            evaluator.run()
            
            return {
                "information_coefficient": evaluator.ic,
                "rank_ic": evaluator.rankic,
                "rre": getattr(evaluator, 'rre', 0.0),
                "pfs1": getattr(evaluator, 'pfs1', 0.0),
                "pfs2": getattr(evaluator, 'pfs2', 0.0),
                "diversity": getattr(evaluator, 'diversity', 0.0),
                "llm_score": getattr(evaluator, 'llm_avg_score', 0.0)
            }
        except FileNotFoundError as e:
            logger.error(f"Qlib data directory not found: {e}")
            logger.info("Please download Qlib data first. Run: python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn")
            logger.info("Falling back to simulated metrics.")
        except Exception as e:
            logger.warning(f"AlphaEval backtest failed: {e}")
            logger.info("Falling back to simulated metrics.")
            
            # Use a deterministic seed based on the code expression for reproducibility
            seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            
            return {
                "information_coefficient": round(rng.uniform(-0.05, 0.15), 3),
                "rank_ic": round(rng.uniform(-0.05, 0.15), 3),
                "rre": round(rng.uniform(0.0, 1.0), 3),
                "pfs1": round(rng.uniform(0.0, 1.0), 6),
                "pfs2": round(rng.uniform(0.0, 1.0), 6),
                "diversity": round(rng.uniform(0.0, 1.0), 3),
                "llm_score": round(rng.uniform(50.0, 100.0), 2),
                "_simulated": True
            }

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        code = state.get("code_expression", "")
        hypothesis_desc = state.get("hypothesis_description", "")
        
        logger.info("[EvalAgent] Starting evaluation and reflexive review")
        
        if not code:
            return {"error": "No code implementation found in state.", "messages": ["[EvalAgent] Error: Missing code."]}
            
        try:
            # 1. Backtesting Module with AlphaEval
            metrics = self._execute_alphaeval_backtest(code)
            is_simulated = metrics.pop("_simulated", False)
            if is_simulated:
                logger.warning("[EvalAgent] Using SIMULATED metrics — results are not real backtest data.")
            logger.info(f"[EvalAgent] Backtest Metrics (simulated={is_simulated}): {metrics}")
            
            # 2. Reflexive Review Module
            review_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a quantitative research director reviewing factor backtest results. "
                           "Analyze the evaluation metrics (IC, Rank IC, RRE, PFS, Diversity, LLM Score) against the original hypothesis. "
                           "Determine if the factor is effective (e.g., IC > 0.02, good Rank IC) and suggest actionable improvements. "
                           "You MUST respond with valid JSON only, no markdown, no explanations."),
                ("user", "Hypothesis: {hypothesis}\nCode: {code}\nMetrics: {metrics}\n\n"
                         "Return ONLY valid JSON matching this exact schema:\n"
                         '{{"review_summary": "string", "is_effective": boolean, "suggested_improvements": "string"}}\n\n'
                         "Do not include markdown code blocks or any other text.")
            ])
            review_chain = review_prompt | self.llm
            raw_review_response = review_chain.invoke({
                "hypothesis": hypothesis_desc,
                "code": code,
                "metrics": str(metrics)
            })
            cleaned_review_json = self._strip_markdown_json(raw_review_response.content)
            review_result = ReflexiveReviewOutput.model_validate_json(cleaned_review_json)
            
            logger.info(f"[EvalAgent] Review Summary: {review_result.review_summary}")
            
            # 3. Save experience to RAG
            self.rag.add_experience(
                hypothesis=hypothesis_desc,
                code=code,
                metrics=metrics,
                is_effective=review_result.is_effective,
                review=review_result.review_summary
            )
            
            return {
                "backtest_metrics": metrics,
                "review_summary": review_result.review_summary,
                "is_effective": review_result.is_effective,
                "is_simulated": is_simulated,
                "suggested_improvements": review_result.suggested_improvements,
                "messages": [
                    f"[EvalAgent] IC: {metrics['information_coefficient']}, Rank IC: {metrics['rank_ic']}, Simulated: {is_simulated}",
                    f"[EvalAgent] Effective: {review_result.is_effective}",
                    f"[EvalAgent] Review: {review_result.review_summary}"
                ]
            }
            
        except Exception as e:
            logger.error(f"[EvalAgent] Failed to evaluate: {e}")
            return {
                "error": str(e),
                "messages": [f"[EvalAgent] Error: {e}"]
            }
