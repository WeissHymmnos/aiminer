from __future__ import annotations

from typing import Any, Dict, List
import json
import re

from loguru import logger

from core.llm import get_llm
from core.strategy import StrategyConfig, StrategyProposalOutput, strategy_templates
from schemas.messages import StrategyProposalBatchOutput
from workflow.state import AlphaMinerState


def candidate_to_strategy_config(
    candidate: Dict[str, Any], state: AlphaMinerState
) -> Dict[str, Any]:
    """Convert a strategy candidate dict (from agent or critic) into a
    validated StrategyConfig payload. Shared by StrategyAgent and StrategyCritic.

    Raises ValueError / pydantic.ValidationError on bad input — callers must
    decide whether to skip or surface the failure.
    """
    market_profile = state.get("market_profile", "cn_stock")
    market_value = "LOCAL_FUTURES" if market_profile == "futures" else market_profile
    payload = {
        "label": f"{candidate.get('template_name', 'generated')}:{state.get('hypothesis_name') or 'alpha'}",
        "strategy_mode": candidate["strategy_mode"],
        "direction": candidate["direction"],
        "selection_rule": candidate["selection_rule"],
        "rebalance_freq": candidate.get("rebalance_freq", "daily"),
        "market": market_value,
        "start_date": state.get("market_analysis_start_date") or "2017-01-01",
        "end_date": state.get("market_analysis_end_date") or "2020-10-31",
        "engine": state.get("evaluation_engine", "polars"),
        "signal_source": "expression",
        "top_n": candidate.get("counts", {}).get("top_n"),
        "bottom_n": candidate.get("counts", {}).get("bottom_n"),
        "long_threshold": candidate.get("thresholds", {}).get("long_threshold"),
        "short_threshold": candidate.get("thresholds", {}).get("short_threshold"),
        "exit_threshold": candidate.get("thresholds", {}).get("exit_threshold"),
        "max_positions": candidate.get("holding_constraints", {}).get("max_positions") or None,
        "max_weight_per_position": candidate.get("holding_constraints", {}).get("max_weight_per_position", 0.1),
        "min_holding_days": candidate.get("holding_constraints", {}).get("min_holding_days", 1),
        "commission_bps": candidate.get("cost_model", {}).get("commission_bps", 5.0),
        "slippage_bps": candidate.get("cost_model", {}).get("slippage_bps", 5.0),
    }
    return StrategyConfig.model_validate(payload).model_dump(mode="json")


class StrategyAgent:
    def __init__(self, provider: str = None, model: str = None, base_url: str = None):
        self.llm = get_llm(
            temperature=0.2,
            provider=provider,
            model_name=model,
            base_url=base_url,
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

    def _fallback_candidates(self, state: AlphaMinerState) -> tuple[str, List[Dict[str, Any]]]:
        market_profile = state.get("market_profile", "cn_stock")
        templates = strategy_templates()
        if market_profile == "futures":
            keys = ["ts_long_short", "ts_long_flat", "cs_top_bottom"]
            execution_style = "ts_trend"
        else:
            keys = ["cs_top_bottom", "cs_top_only", "ts_long_flat"]
            execution_style = "cs_long_short"
        candidates: List[Dict[str, Any]] = []
        for key in keys:
            cfg = templates[key]
            candidates.append(
                StrategyProposalOutput(
                    template_name=key,
                    strategy_mode=cfg.strategy_mode,
                    direction=cfg.direction,
                    selection_rule=cfg.selection_rule,
                    rebalance_freq=cfg.rebalance_freq,
                    thresholds={
                        k: float(v)
                        for k, v in {
                            "long_threshold": cfg.long_threshold,
                            "short_threshold": cfg.short_threshold,
                            "exit_threshold": cfg.exit_threshold,
                        }.items()
                        if v is not None
                    },
                    counts={
                        k: int(v)
                        for k, v in {"top_n": cfg.top_n, "bottom_n": cfg.bottom_n}.items()
                        if v is not None
                    },
                    holding_constraints={
                        "max_positions": cfg.max_positions or 0,
                        "max_weight_per_position": float(cfg.max_weight_per_position),
                        "min_holding_days": int(cfg.min_holding_days),
                    },
                    cost_model={
                        "commission_bps": float(cfg.commission_bps),
                        "slippage_bps": float(cfg.slippage_bps),
                    },
                    rationale=f"Fallback template {key} selected for market_profile={market_profile}.",
                ).model_dump(mode="json")
            )
        return execution_style, candidates

    def _candidate_to_config(self, candidate: Dict[str, Any], state: AlphaMinerState) -> Dict[str, Any]:
        return candidate_to_strategy_config(candidate, state)

    def __call__(self, state: AlphaMinerState) -> Dict[str, Any]:
        market_profile = state.get("market_profile", "cn_stock")
        role_prompt = state.get("role_prompt") or "quantitative research"
        hypothesis = state.get("hypothesis_description", "")
        expression = state.get("code_expression", "")
        factor_metrics = state.get("backtest_metrics", {})

        fallback_execution_style, fallback_candidates = self._fallback_candidates(state)
        system = (
            "You are a quantitative execution researcher. Convert a validated factor into at most 3 tradable strategy candidates. "
            "For cn_stock prefer cross_sectional execution. For futures prefer time_series execution. "
            "Return ONLY valid JSON matching the requested schema."
        )
        user = (
            f"Market profile: {market_profile}\n"
            f"Role: {role_prompt}\n"
            f"Hypothesis: {hypothesis}\n"
            f"Expression: {expression}\n"
            f"Factor metrics: {json.dumps(factor_metrics, ensure_ascii=False)}\n\n"
            "Return JSON with keys execution_style and candidates. "
            "Each candidate must include template_name, strategy_mode, direction, selection_rule, rebalance_freq, "
            "thresholds, counts, holding_constraints, cost_model, rationale."
        )
        try:
            # Invoke the LLM directly — ChatPromptTemplate would interpret
            # the JSON braces in `user` as template variables.
            raw = self.llm.invoke([("system", system), ("user", user)])
            parsed = StrategyProposalBatchOutput.model_validate_json(
                self._strip_markdown_json(raw.content)
            )
            candidates = parsed.candidates[:3]
            if not candidates:
                raise ValueError("No strategy candidates returned")
            normalized: List[Dict[str, Any]] = []
            for item in candidates:
                payload = item.model_dump(mode="json")
                try:
                    config = self._candidate_to_config(payload, state)
                except Exception as cfg_exc:
                    logger.warning(
                        f"[StrategyAgent] Skipping LLM candidate {payload.get('template_name')!r}: {cfg_exc}"
                    )
                    continue
                normalized.append({**payload, "strategy_config": config})
            if not normalized:
                raise ValueError("All LLM candidates failed StrategyConfig validation")
            return {
                "execution_style": parsed.execution_style,
                "strategy_candidates": normalized,
                "messages": [f"[StrategyAgent] Generated {len(normalized)} candidates."],
            }
        except Exception as exc:
            logger.warning(f"[StrategyAgent] Falling back to templates: {exc}")
            normalized = []
            for item in fallback_candidates:
                try:
                    normalized.append(
                        {
                            **item,
                            "strategy_config": self._candidate_to_config(item, state),
                        }
                    )
                except Exception as cfg_exc:
                    logger.error(
                        f"[StrategyAgent] Fallback template {item.get('template_name')!r} invalid: {cfg_exc}"
                    )
            if not normalized:
                logger.error("[StrategyAgent] No usable strategy candidates after fallback.")
                return {
                    "execution_style": fallback_execution_style,
                    "strategy_candidates": [],
                    "messages": ["[StrategyAgent] No usable strategy candidates."],
                }
            return {
                "execution_style": fallback_execution_style,
                "strategy_candidates": normalized,
                "messages": [f"[StrategyAgent] Using {len(normalized)} fallback candidates."],
            }
