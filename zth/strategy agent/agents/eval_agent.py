from typing import Dict, Any
import re

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from workflow.state import AlphaMinerState
from core.rag import RAGModule
from core.llm import get_llm
from schemas.messages import ReflexiveReviewOutput


class EvalAgent:
    """
    EvalAgent evaluates the factor/strategy effectiveness.
    It must not fabricate backtest data when real evaluation is unavailable.
    """

    def __init__(self, rag_module: RAGModule, provider: str = None, model: str = None):
        self.rag = rag_module
        self.llm = get_llm(temperature=0.4, provider=provider, model_name=model)

    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        elif text.startswith("```"):
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _execute_alphaeval_backtest(self, code: str) -> Dict[str, Any]:
        logger.info(f"[EvalAgent] Executing ricequant backtest for expression: {code}")

        try:
            from core.alphaeval.rq_eval import RiceQuantEval

            evaluator = RiceQuantEval(
                factor_expressions=[code],
                test_start_date="2017-01-01",
                test_end_date="2020-10-31",
            )
            evaluator.run()

            return {
                "information_coefficient": evaluator.ic,
                "rank_ic": evaluator.rankic,
                "rre": getattr(evaluator, "rre", 0.0),
                "pfs1": getattr(evaluator, "pfs1", 0.0),
                "pfs2": getattr(evaluator, "pfs2", 0.0),
                "diversity": getattr(evaluator, "diversity", 0.0),
                "llm_score": getattr(evaluator, "llm_avg_score", 0.0),
                "daily_returns": getattr(evaluator, "daily_returns", {}),
                "_evaluation_unavailable": False,
                "_evaluation_note": "",
            }
        except (FileNotFoundError, ValueError, ImportError) as e:
            logger.error(f"ricequant evaluation failed or data not found: {e}")
            return {
                "daily_returns": {},
                "_evaluation_unavailable": True,
                "_evaluation_note": f"RiceQuant evaluation unavailable: {e}",
            }
        except Exception as e:
            logger.warning(f"ricequant backtest failed: {e}")
            return {
                "daily_returns": {},
                "_evaluation_unavailable": True,
                "_evaluation_note": f"RiceQuant backtest failed: {e}",
            }

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        code = state.get("code_expression", "")
        hypothesis_desc = state.get("hypothesis_description", "")
        hypothesis_name = state.get("hypothesis_name", "")
        market_regime = state.get("market_regime_summary", "")
        evaluation_mode = state.get("evaluation_mode", "ricequant")
        iteration = state.get("iteration", 0)
        role_prompt = state.get("role_prompt", "")

        logger.info("[EvalAgent] Starting evaluation and reflexive review")

        if not code:
            return {"error": "No code implementation found in state.", "messages": ["[EvalAgent] Error: Missing code."]}

        try:
            metrics = self._execute_alphaeval_backtest(code)
            evaluation_unavailable = metrics.pop("_evaluation_unavailable", False)
            evaluation_note = metrics.pop("_evaluation_note", "")
            daily_returns = metrics.pop("daily_returns", {})

            if evaluation_unavailable:
                logger.warning(f"[EvalAgent] Real evaluation unavailable: {evaluation_note}")
                review_result = ReflexiveReviewOutput(
                    review_summary=f"No real backtest metrics were produced. {evaluation_note}",
                    is_effective=False,
                    suggested_improvements="Restore RiceQuant/network access, then rerun the evaluation to obtain real metrics.",
                )
            else:
                logger.info(f"[EvalAgent] Backtest Metrics: {metrics}")
                review_prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            "You are a quantitative research director reviewing factor backtest results. "
                            "Analyze the evaluation metrics (IC, Rank IC, RRE, PFS, Diversity, LLM Score) against the original hypothesis. "
                            "Determine if the factor is effective (e.g., IC > 0.02, good Rank IC) and suggest actionable improvements. "
                            "You MUST respond with valid JSON only, no markdown, no explanations.",
                        ),
                        (
                            "user",
                            "Hypothesis: {hypothesis}\nCode: {code}\nMetrics: {metrics}\n\n"
                            "Return ONLY valid JSON matching this exact schema:\n"
                            '{{"review_summary": "string", "is_effective": boolean, "suggested_improvements": "string"}}\n\n'
                            "Do not include markdown code blocks or any other text.",
                        ),
                    ]
                )
                review_chain = review_prompt | self.llm
                raw_review_response = review_chain.invoke(
                    {
                        "hypothesis": hypothesis_desc,
                        "code": code,
                        "metrics": str(metrics),
                    }
                )
                cleaned_review_json = self._strip_markdown_json(raw_review_response.content)
                review_result = ReflexiveReviewOutput.model_validate_json(cleaned_review_json)

            logger.info(f"[EvalAgent] Review Summary: {review_result.review_summary}")

            self.rag.add_experience(
                hypothesis=hypothesis_desc,
                code=code,
                metrics=metrics,
                is_effective=review_result.is_effective,
                review=review_result.review_summary,
                suggested_improvements=review_result.suggested_improvements,
                is_simulated=False,
                evaluation_mode=evaluation_mode,
                market_regime=market_regime,
                iteration=iteration,
                hypothesis_name=hypothesis_name,
                role_prompt=role_prompt,
            )

            current_ic = metrics.get("information_coefficient", 0.0)
            best_ic = state.get("best_ic", -999.0)
            patience_counter = state.get("patience_counter", 0)

            if current_ic > best_ic:
                new_best_ic = current_ic
                new_patience_counter = 0
            else:
                new_best_ic = best_ic
                new_patience_counter = patience_counter + 1

            return {
                "backtest_metrics": metrics,
                "daily_returns": daily_returns,
                "review_summary": review_result.review_summary,
                "is_effective": review_result.is_effective,
                "is_simulated": False,
                "evaluation_unavailable": evaluation_unavailable,
                "evaluation_note": evaluation_note,
                "suggested_improvements": review_result.suggested_improvements,
                "best_ic": new_best_ic,
                "patience_counter": new_patience_counter,
                "messages": [
                    f"[EvalAgent] IC: {metrics.get('information_coefficient')}, Rank IC: {metrics.get('rank_ic')}, Available: {not evaluation_unavailable}",
                    f"[EvalAgent] Effective: {review_result.is_effective}, Mode: {evaluation_mode}",
                    f"[EvalAgent] Review: {review_result.review_summary}",
                ],
            }

        except Exception as e:
            logger.error(f"[EvalAgent] Failed to evaluate: {e}")
            return {
                "error": str(e),
                "messages": [f"[EvalAgent] Error: {e}"],
            }
