# --- Imports ---

from __future__ import annotations
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
import random
import hashlib
import re
from loguru import logger
from aiminer.app_workflow.state import AlphaMinerState
from aiminer.core.constants import MISSING_IC_SENTINEL
from aiminer.core.hybrid_knowledge import HybridKnowledge
from aiminer.core.llm import get_llm
from aiminer.schemas.messages import ReflexiveReviewOutput


# --- EvalAgent Class ---

class EvalAgent:
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
            temperature=0.4,
            provider=provider,
            model_name=model,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )

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

    @classmethod
    def _fallback_review_result(
        cls,
        *,
        metrics: Dict[str, Any],
    ) -> ReflexiveReviewOutput:
        ic = cls._float_metric(metrics.get("information_coefficient", 0.0))
        rank_ic = cls._float_metric(metrics.get("rank_ic", 0.0))
        sharpe = cls._float_metric(metrics.get("sharpe", 0.0))
        max_drawdown = cls._float_metric(metrics.get("max_drawdown", 0.0))
        is_effective = ic > 0.02 and rank_ic > 0.02
        threshold_text = (
            "passes"
            if is_effective
            else "does not pass"
        )
        return ReflexiveReviewOutput(
            review_summary=(
                "LLM review unavailable; using deterministic metric review. "
                f"IC={ic:.4f}, Rank IC={rank_ic:.4f}, Sharpe={sharpe:.4f}, "
                f"Max Drawdown={max_drawdown:.4f}. The factor {threshold_text} "
                "the positive IC and Rank IC effectiveness threshold."
            ),
            is_effective=is_effective,
            suggested_improvements=(
                "Retry review generation later; for the next iteration, refine the "
                "formula to improve both positive IC and Rank IC while monitoring "
                "drawdown and turnover sensitivity."
            ),
        )

    def _review_backtest(
        self,
        *,
        hypothesis_desc: str,
        code: str,
        metrics: Dict[str, Any],
    ) -> ReflexiveReviewOutput:
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
        try:
            review_chain = review_prompt | self.llm
            raw_review_response = review_chain.invoke(
                {"hypothesis": hypothesis_desc, "code": code, "metrics": str(metrics)}
            )
            cleaned_review_json = self._strip_markdown_json(
                getattr(raw_review_response, "content", "") or ""
            )
            if not cleaned_review_json:
                raise ValueError("empty LLM review response")
            return ReflexiveReviewOutput.model_validate_json(cleaned_review_json)
        except Exception as exc:
            logger.warning(
                "[EvalAgent] Review LLM failed; using deterministic fallback review: "
                f"{exc}"
            )
            return self._fallback_review_result(metrics=metrics)

# --- Metric Helpers & Fallback ---

    @staticmethod
    def _simulated_metrics(code: str) -> Dict[str, Any]:
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
            "plot_paths": {},
            "_simulated": True,
        }

    @staticmethod
    def _failed_metrics(error: Exception | str) -> Dict[str, Any]:
        return {
            "information_coefficient": 0.0,
            "rank_ic": 0.0,
            "rre": None,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "daily_returns": {},
            "plot_paths": {},
            "_evaluation_failed": True,
            "evaluation_error": str(error),
        }

    @staticmethod
    def _float_metric(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _add_ic_direction(cls, metrics: Dict[str, Any]) -> Dict[str, Any]:
        ic = cls._float_metric(metrics.get("information_coefficient", 0.0))
        rank_ic = cls._float_metric(metrics.get("rank_ic", 0.0))
        if ic > 0:
            direction = 1
            label = "positive"
        elif ic < 0:
            direction = -1
            label = "negative"
        else:
            direction = 0
            label = "flat"
        metrics["ic_direction"] = direction
        metrics["ic_direction_label"] = label
        metrics["ic_abs"] = abs(ic)
        metrics["rank_ic_abs"] = abs(rank_ic)
        return metrics

    @classmethod
    def _collect_evaluator_metrics(cls, evaluator: Any) -> Dict[str, Any]:
        metrics = {
            "information_coefficient": getattr(evaluator, "ic", 0.0),
            "oos_ic": getattr(evaluator, "oos_ic", getattr(evaluator, "ic", 0.0)),
            "rank_ic": getattr(evaluator, "rankic", 0.0),
            "rre": getattr(evaluator, "rre", 0.0),
            "sharpe": getattr(evaluator, "sharpe", 0.0),
            "max_drawdown": getattr(evaluator, "max_dd", 0.0),
            "plot_paths": getattr(evaluator, "plot_paths", {}) or {},
            "daily_returns": getattr(evaluator, "daily_returns", {}) or {},
        }
        return cls._add_ic_direction(metrics)

    @classmethod
    def _best_ic_abs_from_state(cls, state: AlphaMinerState) -> float:
        if state.get("best_ic_abs") is not None:
            return cls._float_metric(state.get("best_ic_abs"), -1.0)
        best_ic = state.get("best_ic")
        if best_ic is None or cls._float_metric(best_ic, MISSING_IC_SENTINEL) <= -998.0:
            return -1.0
        return abs(cls._float_metric(best_ic, 0.0))

    @staticmethod
    def _build_factor_snapshot(
        state: AlphaMinerState,
        *,
        metrics: Dict[str, Any],
        daily_returns: Dict[str, Any],
        plot_paths: Dict[str, Any],
        review_summary: str,
        is_effective: bool,
        suggested_improvements: str,
        is_simulated: bool,
    ) -> Dict[str, Any]:
        return {
            "iteration": state.get("iteration"),
            "role": state.get("role_prompt"),
            "hypothesis": state.get("hypothesis_name"),
            "hypothesis_name": state.get("hypothesis_name"),
            "hypothesis_description": state.get("hypothesis_description"),
            "rationale": state.get("rationale"),
            "math_formula": state.get("math_formula"),
            "variables_defined": state.get("variables_defined"),
            "code": state.get("code_expression"),
            "code_expression": state.get("code_expression"),
            "metrics": dict(metrics),
            "backtest_metrics": dict(metrics),
            "factor_metrics": dict(metrics),
            "returns": dict(daily_returns or {}),
            "daily_returns": dict(daily_returns or {}),
            "plot_paths": dict(plot_paths or {}),
            "review_summary": review_summary,
            "is_effective": is_effective,
            "factor_is_effective": is_effective,
            "suggested_improvements": suggested_improvements,
            "is_simulated": is_simulated,
            "ic_direction": metrics.get("ic_direction"),
            "ic_direction_label": metrics.get("ic_direction_label"),
        }

# --- Backtest Execution ---

    def _execute_alphaeval_backtest(
        self,
        code: str,
        mode: str = "ricequant",
        engine: str = "pandas",
        test_start_date: str = "2018-01-01",
        test_end_date: str = "2025-12-31",
    ) -> Dict[str, Any]:
        """
        Uses RiceQuantEval or AlphaEval framework to backtest and evaluate.
        """
        logger.info(
            f"[EvalAgent] Executing {mode} backtest (engine={engine}) for expression: {code} "
            f"from {test_start_date} to {test_end_date}"
        )

        try:
            from aiminer.core.evaluator_factory import build_evaluator, evaluation_config_from_mapping

            evaluator = build_evaluator(
                factor_expressions=[code],
                config=evaluation_config_from_mapping(
                    {
                        "data_backend": self._state_data_backend,
                        "evaluation_mode": mode,
                        "evaluation_engine": engine,
                        "market_mode": self._state_market_mode,
                        "market_profile": self._state_market_profile,
                        "market_profiles": self._state_market_profiles,
                        "local_data_path": self._state_local_data_path,
                        "local_data_layout": self._state_local_data_layout,
                        "market_start": test_start_date,
                        "market_end": test_end_date,
                    }
                ),
                test_start_date=test_start_date,
                test_end_date=test_end_date,
            )

            evaluator.run()
        except (FileNotFoundError, ValueError, ImportError) as e:
            logger.error(f"RiceQuant evaluation failed: {e}")
            logger.info("Returning failed real-evaluation metrics; no simulated fallback.")
            return self._add_ic_direction(self._failed_metrics(e))
        except Exception as e:
            logger.warning(f"RiceQuant backtest unexpected failure: {e}")
            logger.info("Returning failed real-evaluation metrics; no simulated fallback.")
            return self._add_ic_direction(self._failed_metrics(e))

        metrics = self._collect_evaluator_metrics(evaluator)
        robustness_fn = getattr(evaluator, "run_robustness_test", None)
        if callable(robustness_fn):
            try:
                robustness_fn()
                refreshed = self._collect_evaluator_metrics(evaluator)
                refreshed.setdefault("daily_returns", metrics.get("daily_returns", {}))
                refreshed.setdefault("plot_paths", metrics.get("plot_paths", {}))
                metrics = refreshed
            except Exception as e:
                logger.warning(
                    "[EvalAgent] Robustness test failed after a successful main "
                    f"backtest; preserving real metrics: {e}"
                )
                metrics["robustness_error"] = str(e)
        return metrics

# --- EvalAgent Entry Point (__call__) ---

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        code = state.get("code_expression", "")
        hypothesis_desc = state.get("hypothesis_description", "")
        mode = state.get("evaluation_mode", "qlib")
        engine = state.get("evaluation_engine", "pandas")
        test_start = state.get("market_analysis_start_date", "2018-01-01")
        test_end = state.get("market_analysis_end_date", "2025-12-31")
        self._state_data_backend = state.get("data_backend", mode)
        self._state_market_mode = state.get("market_mode", "single")
        self._state_market_profile = state.get("market_profile", "cn_stock")
        self._state_market_profiles = state.get("market_profiles") or [self._state_market_profile]
        self._state_local_data_path = state.get("local_data_path")
        self._state_local_data_layout = state.get("local_data_layout", "auto")

        logger.info("[EvalAgent] Starting evaluation and reflexive review")

        if not code:
            return {
                "error": "No code implementation found in state.",
                "messages": ["[EvalAgent] Error: Missing code."],
            }

        try:
            # 1. Backtesting Module
            if not state.get("is_valid_syntax", True):
                syntax_error = state.get("syntax_error") or (
                    "Factor expression failed syntax validation before evaluation."
                )
                logger.warning(
                    "[EvalAgent] Skipping backend evaluation because factor syntax "
                    f"is invalid: {syntax_error}"
                )
                metrics = self._failed_metrics(syntax_error)
            else:
                metrics = self._execute_alphaeval_backtest(
                    code,
                    mode=mode,
                    engine=engine,
                    test_start_date=test_start,
                    test_end_date=test_end,
                )
            is_simulated = metrics.get("_simulated", False)
            evaluation_failed = metrics.get("_evaluation_failed", False)
            daily_returns = metrics.get("daily_returns", {})
            plot_paths = metrics.get("plot_paths", {})
            metrics = {
                k: v
                for k, v in metrics.items()
                if k
                not in (
                    "_simulated",
                    "_evaluation_failed",
                    "daily_returns",
                    "plot_paths",
                )
            }
            metrics = self._add_ic_direction(metrics)
            if is_simulated:
                logger.warning(
                    "[EvalAgent] Using SIMULATED metrics — results are not real backtest data."
                )
            if evaluation_failed:
                logger.warning(
                    "[EvalAgent] Real evaluation failed; using zero metrics for this iteration."
                )
            logger.info(
                "[EvalAgent] Backtest Metrics "
                f"(simulated={is_simulated}, evaluation_failed={evaluation_failed}): {metrics}"
            )

            # 2. Reflexive Review Module
            review_result = self._review_backtest(
                hypothesis_desc=hypothesis_desc,
                code=code,
                metrics=metrics,
            )

            logger.info(f"[EvalAgent] Review Summary: {review_result.review_summary}")

            # 3. Save experience to RAG (Vector fallback) - ONLY if it's real data
            if not is_simulated and not evaluation_failed:
                self.knowledge.rag.add_experience(
                    hypothesis=hypothesis_desc,
                    code=code,
                    metrics=metrics,
                    is_effective=review_result.is_effective,
                    review=review_result.review_summary,
                )
            else:
                logger.warning(
                    "[EvalAgent] Skipping RAG update: Metrics are simulated or evaluation failed."
                )

            # 4. Update Early Stopping Metrics
            # IMPORTANT: Simulated metrics must NOT update best_ic or patience counter —
            # fake high IC from quota-exceeded fallback would otherwise trigger early stop
            # and freeze the patience counter at 0, preventing any real exploration.
            current_ic = self._float_metric(metrics.get("information_coefficient", 0.0))
            current_ic_abs = abs(current_ic)
            best_ic = state.get("best_ic", MISSING_IC_SENTINEL)
            best_ic_abs = self._best_ic_abs_from_state(state)
            patience_counter = state.get("patience_counter", 0)
            best_snapshot = state.get("best_factor_snapshot")

            if is_simulated:
                # Freeze all early-stopping state; treat this iteration as a no-op
                logger.warning(
                    "[EvalAgent] Simulated metrics detected — best_ic and patience_counter unchanged."
                )
                new_best_ic = best_ic
                new_best_ic_abs = best_ic_abs
                new_patience_counter = patience_counter
                new_best_code = state.get("best_code_expression")
                new_best_snapshot = best_snapshot
            elif evaluation_failed:
                logger.warning(
                    "[EvalAgent] Evaluation failure counted as an unproductive iteration."
                )
                new_best_ic = best_ic
                new_best_ic_abs = best_ic_abs
                new_patience_counter = patience_counter + 1
                new_best_code = state.get("best_code_expression")
                new_best_snapshot = best_snapshot
            elif current_ic_abs > best_ic_abs:
                new_best_ic = current_ic
                new_best_ic_abs = current_ic_abs
                new_patience_counter = 0
                new_best_code = code
                new_best_snapshot = self._build_factor_snapshot(
                    state,
                    metrics=metrics,
                    daily_returns=daily_returns,
                    plot_paths=plot_paths,
                    review_summary=review_result.review_summary,
                    is_effective=review_result.is_effective,
                    suggested_improvements=review_result.suggested_improvements,
                    is_simulated=is_simulated,
                )
            else:
                new_best_ic = best_ic
                new_best_ic_abs = best_ic_abs
                new_patience_counter = patience_counter + 1
                new_best_code = state.get("best_code_expression")
                new_best_snapshot = best_snapshot

            return {
                "backtest_metrics": metrics,
                "factor_metrics": metrics,
                "daily_returns": daily_returns,
                "plot_paths": plot_paths,
                "ic_direction": metrics.get("ic_direction", 0),
                "ic_direction_label": metrics.get("ic_direction_label", "flat"),
                "review_summary": review_result.review_summary,
                "is_effective": review_result.is_effective,
                "factor_is_effective": review_result.is_effective,
                "is_simulated": is_simulated,
                "evaluation_failed": evaluation_failed,
                "evaluation_error": metrics.get("evaluation_error"),
                "suggested_improvements": review_result.suggested_improvements,
                "best_ic": new_best_ic,
                "best_ic_abs": new_best_ic_abs,
                "best_code_expression": new_best_code,
                "best_factor_snapshot": new_best_snapshot,
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
