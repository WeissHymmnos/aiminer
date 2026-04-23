from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from loguru import logger

from agents.strategy_agent import candidate_to_strategy_config
from core.llm import get_llm
from schemas.messages import RefinementProposalOutput
from app_workflow.state import AlphaMinerState


# Convergence guards. These live as module constants so they can be tweaked or
# patched in tests without rebuilding a critic instance.
DEFAULT_IMPROVEMENT_EPSILON = 0.05  # require >5% selection_score lift to keep iterating
DEFAULT_MAX_REFINEMENT_ROUNDS = 2
MAX_PROPOSALS_PER_ROUND = 2


def _strip_markdown_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    elif text.startswith("```"):
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _config_signature(config: Dict[str, Any]) -> tuple:
    """A hashable signature used to deduplicate proposals against the current
    best config and against each other within a round."""
    if not config:
        return tuple()
    keys = (
        "strategy_mode",
        "direction",
        "selection_rule",
        "rebalance_freq",
        "top_n",
        "bottom_n",
        "long_threshold",
        "short_threshold",
        "exit_threshold",
        "max_positions",
        "max_weight_per_position",
        "min_holding_days",
        "commission_bps",
        "slippage_bps",
    )
    return tuple(config.get(k) for k in keys)


def _improvement_satisfied(
    current_score: float,
    previous_score: float | None,
    epsilon: float = DEFAULT_IMPROVEMENT_EPSILON,
) -> bool:
    """Decide whether the latest round improved enough to justify another loop.

    For positive previous scores we require multiplicative lift; for non-positive
    scores any meaningful absolute improvement counts so we don't get stuck on
    tiny negatives.
    """
    if previous_score is None:
        return True
    if previous_score <= 0:
        return current_score > previous_score + abs(epsilon)
    return current_score > previous_score * (1.0 + epsilon)


class StrategyCritic:
    """Reflexion-style critic: read the latest strategy_results and emit
    targeted refinements that swap in a new strategy_candidates list.

    Returns a state delta — never mutates the input state directly.
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        base_url: str = None,
        reasoning_effort: str = None,
    ):
        self.llm = get_llm(
            temperature=0.3,
            provider=provider,
            model_name=model,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        round_idx = int(state.get("strategy_refinement_round", 0))
        max_rounds = int(
            state.get("max_strategy_refinement_rounds", DEFAULT_MAX_REFINEMENT_ROUNDS)
        )
        history: List[Dict[str, Any]] = list(state.get("strategy_refinement_history") or [])
        best_result = state.get("best_strategy_result") or {}
        best_metrics = best_result.get("metrics") or state.get("best_strategy_metrics") or {}
        current_score = float(state.get("selection_score", 0.0) or 0.0)

        # Stop conditions checked before paying for an LLM call ----------------
        previous_score = history[-1]["selection_score"] if history else None
        if not _improvement_satisfied(current_score, previous_score):
            logger.info(
                f"[StrategyCritic] No meaningful lift ({previous_score} → {current_score}); halting refinement."
            )
            return self._halt(state, history, current_score, reason="no_improvement")
        if round_idx >= max_rounds:
            logger.info(f"[StrategyCritic] Max refinement rounds ({max_rounds}) reached.")
            return self._halt(state, history, current_score, reason="max_rounds")
        if not best_result or not best_metrics:
            logger.info("[StrategyCritic] No best strategy to reflect on; halting.")
            return self._halt(state, history, current_score, reason="no_best")

        try:
            proposal = self._invoke_llm(state, best_result, best_metrics, history)
        except Exception as exc:
            logger.warning(f"[StrategyCritic] LLM critique failed: {exc}; halting refinement.")
            return self._halt(state, history, current_score, reason="llm_error")

        if not proposal.should_continue or not proposal.proposals:
            logger.info("[StrategyCritic] Critic chose to stop (should_continue=False or empty).")
            return self._halt(
                state,
                history,
                current_score,
                reason="critic_stop",
                failure_modes=proposal.failure_modes,
                rationale=proposal.rationale,
            )

        # Materialize candidates with dedupe vs current best + intra-batch ----
        current_signature = _config_signature(best_result.get("strategy_config") or {})
        seen_signatures: set[tuple] = {current_signature}
        normalized: List[Dict[str, Any]] = []
        for item in proposal.proposals[:MAX_PROPOSALS_PER_ROUND]:
            payload = item.model_dump(mode="json")
            try:
                config = candidate_to_strategy_config(payload, state)
            except Exception as cfg_exc:
                logger.warning(
                    f"[StrategyCritic] Skipping invalid proposal {payload.get('template_name')!r}: {cfg_exc}"
                )
                continue
            signature = _config_signature(config)
            if signature in seen_signatures:
                logger.debug(
                    f"[StrategyCritic] Dropping duplicate proposal {payload.get('template_name')!r}."
                )
                continue
            seen_signatures.add(signature)
            normalized.append({**payload, "strategy_config": config})

        if not normalized:
            logger.info("[StrategyCritic] All proposals were duplicates or invalid; halting.")
            return self._halt(
                state,
                history,
                current_score,
                reason="no_novel_proposals",
                failure_modes=proposal.failure_modes,
                rationale=proposal.rationale,
            )

        history_entry = {
            "round": round_idx,
            "selection_score": current_score,
            "best_strategy_id": best_result.get("strategy_id"),
            "failure_modes": list(proposal.failure_modes),
            "rationale": proposal.rationale,
            "proposed_count": len(normalized),
        }
        history.append(history_entry)

        return {
            "strategy_candidates": normalized,
            "strategy_refinement_round": round_idx + 1,
            "strategy_refinement_history": history,
            "messages": [
                f"[StrategyCritic] Round {round_idx + 1}: proposed {len(normalized)} refined candidates "
                f"(failure_modes={proposal.failure_modes})."
            ],
        }

    # ------------------------------------------------------------------ helpers
    def _halt(
        self,
        state: AlphaMinerState,
        history: List[Dict[str, Any]],
        current_score: float,
        *,
        reason: str,
        failure_modes: List[str] | None = None,
        rationale: str | None = None,
    ) -> Dict[str, Any]:
        history.append(
            {
                "round": int(state.get("strategy_refinement_round", 0)),
                "selection_score": current_score,
                "best_strategy_id": (state.get("best_strategy_result") or {}).get("strategy_id"),
                "halt_reason": reason,
                "failure_modes": list(failure_modes or []),
                "rationale": rationale,
                "proposed_count": 0,
            }
        )
        return {
            "strategy_refinement_history": history,
            "messages": [f"[StrategyCritic] Halt ({reason})."],
        }

    def _invoke_llm(
        self,
        state: AlphaMinerState,
        best_result: Dict[str, Any],
        best_metrics: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> RefinementProposalOutput:
        period_metrics = best_result.get("period_metrics") or {}
        trade_stats = best_result.get("trade_stats") or {}
        walk_forward = best_result.get("walk_forward") or {}
        config = best_result.get("strategy_config") or {}
        history_snippet = [
            {
                "round": h.get("round"),
                "selection_score": h.get("selection_score"),
                "failure_modes": h.get("failure_modes"),
                "halt_reason": h.get("halt_reason"),
            }
            for h in history[-3:]
        ]

        system = (
            "You are a quantitative strategy critic. Read the realized backtest of the current best "
            "strategy and propose at most 2 refined strategy candidates that target the dominant "
            "failure modes. Adjust ONLY strategy_config-level fields (selection_rule, thresholds, "
            "counts, rebalance_freq, holding_constraints, cost_model). NEVER change the factor "
            "expression. If the metrics already look strong or you cannot diagnose a fixable issue, "
            "set should_continue=false and return an empty proposals list. Output strictly valid JSON."
        )
        user = (
            f"Market profile: {state.get('market_profile', 'cn_stock')}\n"
            f"Factor expression: {state.get('code_expression', '')[:400]}\n"
            f"Current best strategy_config: {json.dumps(config, ensure_ascii=False, default=str)}\n"
            f"Headline metrics: {json.dumps(best_metrics, ensure_ascii=False, default=str)}\n"
            f"Trade stats: {json.dumps(trade_stats, ensure_ascii=False, default=str)}\n"
            f"Period metrics (yearly/quarterly/worst_months): "
            f"{json.dumps(period_metrics, ensure_ascii=False, default=str)[:1500]}\n"
            f"Walk-forward (per-window OOS metrics + aggregate stability): "
            f"{json.dumps(walk_forward, ensure_ascii=False, default=str)[:1200]}\n"
            f"Refinement history (most recent first): "
            f"{json.dumps(history_snippet, ensure_ascii=False, default=str)}\n\n"
            "Return JSON with keys: failure_modes (List[str]), proposals (List of strategy candidates "
            "matching the StrategyCandidateOutput schema), should_continue (bool), rationale (str)."
        )

        # Invoke the LLM directly — building a ChatPromptTemplate would treat
        # the JSON braces in `user` as template variables.
        raw = self.llm.invoke([("system", system), ("user", user)])
        return RefinementProposalOutput.model_validate_json(_strip_markdown_json(raw.content))
