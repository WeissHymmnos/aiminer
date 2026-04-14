from __future__ import annotations
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
import random
import hashlib
import re
from loguru import logger
from workflow.state import AlphaMinerState
from core.hybrid_knowledge import HybridKnowledge
from core.llm import get_llm
from schemas.messages import ReflexiveReviewOutput


class EvalAgent:
    def __init__(
        self, knowledge: HybridKnowledge, provider: str = None, model: str = None
    ):
        self.knowledge = knowledge
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

    def _execute_alphaeval_backtest(
        self,
        code: str,
        mode: str = "ricequant",
        engine: str = "pandas",
        test_start_date: str = "2018-01-01",
        test_end_date: str = "2025-12-31",
    ) -> Dict[str, float]:
        """
        Uses RiceQuantEval or AlphaEval framework to backtest and evaluate.
        """
        logger.info(
            f"[EvalAgent] Executing {mode} backtest (engine={engine}) for expression: {code} "
            f"from {test_start_date} to {test_end_date}"
        )

        try:
            if mode.lower() == "qlib":
                from core.alphaeval.modeltester import AlphaEval

                evaluator = AlphaEval(
                    factor_expressions=[code],
                    test_start_date=test_start_date,
                    test_end_date=test_end_date,
                )
            else:
                from core.alphaeval.rq_eval import RiceQuantEval

                evaluator = RiceQuantEval(
                    factor_expressions=[code],
                    test_start_date=test_start_date,
                    test_end_date=test_end_date,
                    engine=engine,
                )

            evaluator.run()
            evaluator.run_robustness_test()

            return {
                "information_coefficient": evaluator.ic,
                "oos_ic": getattr(evaluator, "oos_ic", evaluator.ic),
                "rank_ic": getattr(evaluator, "rankic", 0.0),
                "rre": getattr(evaluator, "rre", 0.0),
                "sharpe": getattr(evaluator, "sharpe", 0.0),
                "max_drawdown": getattr(evaluator, "max_dd", 0.0),
                "plot_paths": getattr(evaluator, "plot_paths", {}),
                "daily_returns": getattr(evaluator, "daily_returns", {}),
            }
        except (FileNotFoundError, ValueError, ImportError) as e:
            logger.error(f"RiceQuant evaluation failed: {e}")
            logger.info("Falling back to simulated metrics.")

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
                "daily_returns": {},
                "_simulated": True,
            }
        except Exception as e:
            logger.warning(f"RiceQuant backtest unexpected failure: {e}")
            logger.info("Falling back to simulated metrics.")

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
                "daily_returns": {},
                "_simulated": True,
            }

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        code = state.get("code_expression", "")
        hypothesis_desc = state.get("hypothesis_description", "")
        mode = state.get("evaluation_mode", "qlib")
        engine = state.get("evaluation_engine", "pandas")
        test_start = state.get("market_analysis_start_date", "2018-01-01")
        test_end = state.get("market_analysis_end_date", "2025-12-31")

        logger.info("[EvalAgent] Starting evaluation and reflexive review")

        if not code:
            return {
                "error": "No code implementation found in state.",
                "messages": ["[EvalAgent] Error: Missing code."],
            }

        try:
            # 1. Backtesting Module
            metrics = self._execute_alphaeval_backtest(
                code,
                mode=mode,
                engine=engine,
                test_start_date=test_start,
                test_end_date=test_end,
            )
            is_simulated = metrics.get("_simulated", False)
            daily_returns = metrics.get("daily_returns", {})
            plot_paths = metrics.get("plot_paths", {})
            metrics = {
                k: v
                for k, v in metrics.items()
                if k not in ("_simulated", "daily_returns", "plot_paths")
            }
            if is_simulated:
                logger.warning(
                    "[EvalAgent] Using SIMULATED metrics — results are not real backtest data."
                )
            logger.info(
                f"[EvalAgent] Backtest Metrics (simulated={is_simulated}): {metrics}"
            )

            # 2. Reflexive Review Module
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
                {"hypothesis": hypothesis_desc, "code": code, "metrics": str(metrics)}
            )
            cleaned_review_json = self._strip_markdown_json(raw_review_response.content)
            review_result = ReflexiveReviewOutput.model_validate_json(
                cleaned_review_json
            )

            logger.info(f"[EvalAgent] Review Summary: {review_result.review_summary}")

            # 3. Save experience to RAG (Vector fallback) - ONLY if it's real data
            if not is_simulated:
                self.knowledge.rag.add_experience(
                    hypothesis=hypothesis_desc,
                    code=code,
                    metrics=metrics,
                    is_effective=review_result.is_effective,
                    review=review_result.review_summary,
                )
            else:
                logger.warning(
                    "[EvalAgent] Skipping RAG update: Metrics are simulated."
                )

            # 4. Update Early Stopping Metrics
            # IMPORTANT: Simulated metrics must NOT update best_ic or patience counter —
            # fake high IC from quota-exceeded fallback would otherwise trigger early stop
            # and freeze the patience counter at 0, preventing any real exploration.
            current_ic = metrics.get("information_coefficient", 0.0)
            best_ic = state.get("best_ic", -999.0)
            patience_counter = state.get("patience_counter", 0)

            if is_simulated:
                # Freeze all early-stopping state; treat this iteration as a no-op
                logger.warning(
                    "[EvalAgent] Simulated metrics detected — best_ic and patience_counter unchanged."
                )
                new_best_ic = best_ic
                new_patience_counter = patience_counter
                new_best_code = state.get("best_code_expression", code)
            elif current_ic > best_ic:
                new_best_ic = current_ic
                new_patience_counter = 0
                new_best_code = code
            else:
                new_best_ic = best_ic
                new_patience_counter = patience_counter + 1
                new_best_code = state.get("best_code_expression", code)

            return {
                "backtest_metrics": metrics,
                "daily_returns": daily_returns,
                "plot_paths": plot_paths,
                "review_summary": review_result.review_summary,
                "is_effective": review_result.is_effective,
                "is_simulated": is_simulated,
                "suggested_improvements": review_result.suggested_improvements,
                "best_ic": new_best_ic,
                "best_code_expression": new_best_code,
                "patience_counter": new_patience_counter,
                "messages": [
                    f"[EvalAgent] IC: {metrics['information_coefficient']}, Rank IC: {metrics['rank_ic']}, Simulated: {is_simulated}",
                    f"[EvalAgent] Effective: {review_result.is_effective}",
                    f"[EvalAgent] Review: {review_result.review_summary}",
                ],
            }

        except Exception as e:
            logger.error(f"[EvalAgent] Failed to evaluate: {e}")
            return {"error": str(e), "messages": [f"[EvalAgent] Error: {e}"]}
