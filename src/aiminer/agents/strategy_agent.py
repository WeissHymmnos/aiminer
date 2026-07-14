# --- Imports & Constants ---

from __future__ import annotations

from typing import Any, Dict, List
import json
import re

from loguru import logger

from aiminer.core.llm import get_llm
from aiminer.core.strategy import StrategyConfig, StrategyProposalOutput, strategy_templates
from aiminer.schemas.messages import StrategyProposalBatchOutput
from aiminer.app_workflow.state import AlphaMinerState


# --- Normalization Utilities ---

def _normalized_token(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[\s\-/]+", "_", text.strip().lower())


def _text_contains_any(value: Any, needles: tuple[str, ...]) -> bool:
    text = str(value or "").strip().lower()
    token = _normalized_token(value)
    return any(needle in text or needle in token for needle in needles)


def _strategy_mode_hint(value: Any) -> str | None:
    token = _normalized_token(value)
    if token.startswith(("cs_", "cross_sectional", "cross_section", "crosssectional")):
        return "cross_sectional"
    if token.endswith("_cs") or "_cs_" in token:
        return "cross_sectional"
    if token.startswith(("ts_", "time_series", "timeseries")):
        return "time_series"
    if token.endswith("_ts") or "_ts_" in token:
        return "time_series"
    if token in {
        "cross_sectional",
        "cross_section",
        "crosssectional",
    } or _text_contains_any(value, ("cross_sectional", "cross_section", "cross-sectional")):
        return "cross_sectional"
    if token in {"time_series", "timeseries"} or _text_contains_any(
        value, ("time_series", "time-series", "timeseries")
    ):
        return "time_series"
    return None


def _clean_positive_ints(values: Dict[str, Any] | None) -> Dict[str, int]:
    cleaned: Dict[str, int] = {}
    for key, value in (values or {}).items():
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            continue
        if int_value >= 1:
            cleaned[key] = int_value
    return cleaned


def _clean_floats(values: Dict[str, Any] | None) -> Dict[str, float]:
    cleaned: Dict[str, float] = {}
    for key, value in (values or {}).items():
        try:
            cleaned[key] = float(value)
        except (TypeError, ValueError):
            continue
    return cleaned


def _fraction_from_count_alias(value: Any) -> float | None:
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        return None
    if not 0 < fraction < 100:
        return None
    if fraction > 1:
        fraction = fraction / 100.0
    return fraction if 0 < fraction < 1 else None


def _thresholds_from_quantile_counts(values: Dict[str, Any] | None) -> Dict[str, float]:
    thresholds: Dict[str, float] = {}
    for key, value in (values or {}).items():
        token = _normalized_token(key)
        fraction = _fraction_from_count_alias(value)
        if fraction is None:
            continue
        if token in {
            "quantile_long",
            "long_quantile",
            "top_quantile",
            "long_pct",
            "top_pct",
            "long_percent",
            "top_percent",
            "long_percentile",
            "top_percentile",
        }:
            thresholds.setdefault("long_threshold", 1.0 - fraction)
        elif token in {
            "quantile_short",
            "short_quantile",
            "bottom_quantile",
            "short_pct",
            "bottom_pct",
            "short_percent",
            "bottom_percent",
            "short_percentile",
            "bottom_percentile",
        }:
            thresholds.setdefault("short_threshold", fraction)
    return thresholds


def _merge_structured_selection_rule(payload: Dict[str, Any]) -> Dict[str, Any]:
    selection_rule = payload.get("selection_rule")
    if not isinstance(selection_rule, dict):
        return payload

    merged = dict(payload)
    thresholds = dict(merged.get("thresholds") or {})
    counts = dict(merged.get("counts") or {})

    method = None
    for key, value in selection_rule.items():
        token = _normalized_token(key)
        if token in {"method", "rule", "selection_rule", "type", "mode", "name"}:
            if value not in (None, ""):
                method = value
            continue
        if token in {
            "long_threshold",
            "long_entry_threshold",
            "entry_long_threshold",
            "upper_threshold",
            "buy_threshold",
        }:
            thresholds.setdefault("long_threshold", value)
        elif token in {
            "short_threshold",
            "short_entry_threshold",
            "entry_short_threshold",
            "lower_threshold",
            "sell_threshold",
        }:
            thresholds.setdefault("short_threshold", value)
        elif token in {
            "exit_threshold",
            "neutral_threshold",
            "flat_threshold",
            "close_threshold",
        }:
            thresholds.setdefault("exit_threshold", value)
        elif token in {
            "top_n",
            "long_n",
            "num_long",
            "long_count",
            "top_count",
            "n_long",
        }:
            counts.setdefault("top_n", value)
        elif token in {
            "bottom_n",
            "short_n",
            "num_short",
            "short_count",
            "bottom_count",
            "n_short",
        }:
            counts.setdefault("bottom_n", value)
        elif token in {
            "quantile_long",
            "long_quantile",
            "top_quantile",
            "long_pct",
            "top_pct",
            "long_percent",
            "top_percent",
            "long_percentile",
            "top_percentile",
            "quantile_short",
            "short_quantile",
            "bottom_quantile",
            "short_pct",
            "bottom_pct",
            "short_percent",
            "bottom_percent",
            "short_percentile",
            "bottom_percentile",
        }:
            counts.setdefault(token, value)

    if method is None:
        if thresholds:
            method = "threshold"
        elif "top_n" in counts and "bottom_n" in counts:
            method = "top_bottom_n"
        elif "top_n" in counts:
            method = "top_n"
        elif "bottom_n" in counts:
            method = "bottom_n"
        else:
            method = "threshold"

    merged["selection_rule"] = method
    merged["thresholds"] = thresholds
    merged["counts"] = counts
    return merged


def _clean_holding_constraints(values: Dict[str, Any] | None) -> Dict[str, float | int]:
    cleaned: Dict[str, float | int] = {}
    raw = values or {}

    try:
        max_positions = int(raw.get("max_positions"))
    except (TypeError, ValueError):
        max_positions = None
    if max_positions is not None and max_positions >= 1:
        cleaned["max_positions"] = max_positions

    try:
        max_weight = float(raw.get("max_weight_per_position"))
    except (TypeError, ValueError):
        max_weight = None
    if max_weight is not None:
        if max_weight > 1.0 and max_weight <= 100.0:
            max_weight = max_weight / 100.0
        if 0 < max_weight <= 1.0:
            cleaned["max_weight_per_position"] = max_weight

    try:
        min_holding_days = int(raw.get("min_holding_days"))
    except (TypeError, ValueError):
        min_holding_days = None
    if min_holding_days is not None and min_holding_days >= 1:
        cleaned["min_holding_days"] = min_holding_days

    return cleaned


def _clean_cost_model(values: Dict[str, Any] | None) -> Dict[str, float]:
    cleaned: Dict[str, float] = {}
    for key in ("commission_bps", "slippage_bps"):
        try:
            value = float((values or {}).get(key))
        except (TypeError, ValueError):
            continue
        if value >= 0:
            cleaned[key] = value
    return cleaned


def _normalize_strategy_mode(
    value: Any, market_profile: str, context_hint: Any = None
) -> str:
    token = _normalized_token(value)
    hinted_mode = _strategy_mode_hint(context_hint)
    if token.startswith(("cross_sectional", "cross_section", "crosssectional", "cs_")):
        return "cross_sectional"
    if token.startswith(("time_series", "timeseries", "ts_")):
        return "time_series"
    if token in {
        "cross_sectional",
        "cross_section",
        "crosssectional",
        "cs",
        "ranking",
        "rank",
        "rank_based",
        "rank_based_strategy",
        "rank_strategy",
        "statistical_arbitrage",
        "stat_arb",
        "arbitrage",
        "alpha",
        "alpha_strategy",
        "cross_sectional_alpha",
        "alpha_long_short",
        "multi_long_short",
        "multi_asset_long_short",
        "multi_instrument_long_short",
        "portfolio_long_short",
        "cross_asset_long_short",
        "cross_sectional_long_short",
        "long_short_portfolio",
    }:
        return "cross_sectional"
    if token in {
        "time_series",
        "timeseries",
        "time_series_strategy",
        "ts",
        "cta",
        "cta_strategy",
        "managed_futures",
        "single_asset",
        "single_asset_strategy",
        "single_asset_time_series",
        "single_instrument",
        "single_contract",
        "multi_asset",
        "multi_asset_strategy",
        "multi_instrument",
        "multi_instrument_strategy",
        "multi_asset_signal",
        "portfolio",
        "portfolio_signal",
        "cross_asset",
        "cross_asset_signal",
        "signal",
        "signal_based",
        "trend",
        "trend_following",
        "mean_reversion",
        "event_driven",
        "long_short",
        "longshort",
        "long_and_short",
        "single_leg",
        "single_leg_strategy",
        "single_long",
        "single_long_strategy",
        "single_short",
        "single_short_strategy",
        "one_leg",
        "one_leg_strategy",
        "dual_leg",
        "dual_leg_strategy",
        "two_leg",
        "two_legs",
        "two_leg_strategy",
        "long_only",
        "short_only",
        "long",
        "short",
        "both",
        "simple",
        "simple_strategy",
        "composite",
        "composite_strategy",
        "generated",
        "generated_strategy",
        "generic",
        "generic_strategy",
        "mixed",
        "mixed_strategy",
        "hybrid",
        "hybrid_strategy",
        "hybrid_factor",
        "futures_hybrid",
        "futures_hybrid_factor",
        "combined",
        "combined_strategy",
        "absolute",
        "absolute_momentum",
        "absolute_signal",
        "absolute_threshold",
        "absolute_thresholds",
        "continuous",
        "continuous_signal",
        "continuous_strategy",
        "continuous_signal_strategy",
        "signal_continuous",
        "threshold",
        "threshold_strategy",
        "threshold_based",
        "threshold_based_strategy",
        "signal_threshold",
        "signal_threshold_strategy",
        "quantile_threshold",
        "quantile_threshold_strategy",
        "percentile_threshold",
        "percentile_threshold_strategy",
        "ma_cross",
        "ma_cross_strategy",
        "ma_crossover",
        "ma_crossover_strategy",
        "moving_average_cross",
        "moving_average_cross_strategy",
        "moving_average_crossover",
        "moving_average_crossover_strategy",
        "crossover",
        "crossover_strategy",
        "cross_over",
        "cross_over_strategy",
        "momentum",
        "momentum_divergence",
        "price_volume_divergence",
        "price_volume_correlation",
        "price_volume_correlation_shift",
        "price_volume_regime",
        "breakout",
        "breakout_strategy",
        "breakout_signal",
        "breakout_momentum",
        "volume_breakout",
        "volume_confirmed_breakout",
        "divergence",
        "reversal",
    }:
        if hinted_mode:
            return hinted_mode
        return "time_series" if market_profile == "futures" else "cross_sectional"
    if _text_contains_any(
        value,
        (
            "\u8d8b\u52bf\u8ddf\u8e2a",
            "\u5747\u503c\u56de\u590d",
            "\u4e8b\u4ef6\u9a71\u52a8",
            "\u65f6\u95f4\u5e8f\u5217",
            "\u65f6\u5e8f",
            "trend_following",
            "mean_reversion",
            "event_driven",
            "time_series",
            "timeseries",
        ),
    ):
        return "time_series" if market_profile == "futures" else "cross_sectional"
    if hinted_mode:
        return hinted_mode
    return str(value)


def _selection_mentions_short(value: Any) -> bool:
    return _text_contains_any(
        value,
        (
            "short",
            "sell",
            "\u505a\u7a7a",
            "\u7a7a\u5934",
            "\u53ea\u7a7a",
            "go_short",
            "short_only",
        ),
    )


def _normalize_direction(value: Any, strategy_mode: str, selection_rule_text: Any) -> str:
    raw_text = "" if value is None else str(value).strip().lower()
    token = _normalized_token(value)
    if token in {
        "long_short",
        "longshort",
        "long_and_short",
        "both",
        "both_legs",
        "both_leg",
        "both_sides",
        "dual",
        "bidirectional",
        "bi_directional",
        "both_directions",
        "two_way",
        "two_way_directional",
        "two_sided",
        "long_high_short_low",
        "long_low_short_high",
        "top_long_bottom_short",
        "top_long_short_bottom",
        "long_top_bottom_short",
        "long_short_both",
        "factor_long_short",
        "factor_longshort",
        "factor_long_and_short",
        "neutral",
        "market_neutral",
        "factor_neutral",
        "dollar_neutral",
        "beta_neutral",
        "contrarian",
        "mean_reversion",
        "mean_reverting",
        "reversion",
        "reversal",
        "countertrend",
        "counter_trend",
        "counter_trend_reversal",
    } or _text_contains_any(
        value, ("\u591a\u7a7a", "\u53cc\u5411", "\u4e2d\u6027", "long_short", "bidirectional", "neutral")
    ):
        return "long_short"
    if "long" in token and "short" in token:
        return "long_short"
    if token in {"1", "true", "yes"} or raw_text in {"1.0", "+1", "+1.0", "-1", "-1.0"}:
        return "long_short"
    if token in {"long_flat", "longflat", "flat"} or _text_contains_any(
        value, ("\u7a7a\u4ed3", "flat")
    ):
        return "long_flat"
    if token in {"0", "false", "no"}:
        return "long_flat" if strategy_mode == "time_series" else "long_only"
    if token in {"short", "short_only", "shortonly"} or _text_contains_any(
        value, ("\u505a\u7a7a", "\u7a7a\u5934", "\u53ea\u7a7a", "go_short", "short", "short_only")
    ):
        return "long_short"
    if token in {
        "factor_short",
        "short_factor",
        "inverse_factor",
        "negative",
        "negative_factor",
        "factor_negative",
    }:
        return "long_short"
    if token in {
        "long",
        "long_only",
        "longonly",
        "factor_long",
        "long_factor",
        "positive",
        "factor_positive",
        "positive_factor",
        "long_high",
        "high_long",
        "long_top",
        "top_long",
        "top_long_only",
        "long_top_only",
        "top_only_long",
        "long_positive",
        "positive_long",
    } or _text_contains_any(
        value, ("\u505a\u591a", "\u591a\u5934", "\u53ea\u591a", "go_long", "long", "long_only")
    ):
        if strategy_mode == "time_series":
            return "long_short" if _selection_mentions_short(selection_rule_text) else "long_flat"
        return "long_only"
    return str(value)


def _normalize_selection_rule(value: Any, strategy_mode: str) -> str:
    token = _normalized_token(value)
    top_hint = _text_contains_any(
        value,
        (
            "highest",
            "largest",
            "top_ranked",
            "top ranked",
            "\u6700\u9ad8",
            "\u8f83\u9ad8",
            "\u9ad8\u7684",
            "\u6392\u540d\u524d",
            "\u56e0\u5b50\u503c\u9ad8",
            "\u505a\u591a",
            "\u591a\u5934",
            "highest_ranked",
            "higher",
            "high",
            "top_rank",
            "factor_value_high",
            "go_long",
            "long",
        ),
    )
    bottom_hint = _text_contains_any(
        value,
        (
            "lowest",
            "smallest",
            "bottom_ranked",
            "bottom ranked",
            "\u6700\u4f4e",
            "\u8f83\u4f4e",
            "\u4f4e\u7684",
            "\u6392\u540d\u540e",
            "\u56e0\u5b50\u503c\u4f4e",
            "\u505a\u7a7a",
            "\u7a7a\u5934",
            "lowest_ranked",
            "lower",
            "low",
            "bottom_rank",
            "factor_value_low",
            "go_short",
            "short",
        ),
    )
    if token in {
        "top_n",
        "top",
        "top_quantile",
        "top_percentile",
        "top_quartile",
    }:
        return "threshold" if strategy_mode == "time_series" else "top_n"
    if token in {
        "bottom_n",
        "bottom",
        "bottom_quantile",
        "bottom_percentile",
        "bottom_quartile",
    }:
        return "threshold" if strategy_mode == "time_series" else "bottom_n"
    if token in {
        "top_bottom_n",
        "top_bottom",
        "topbottom",
        "top_and_bottom",
        "top_n_and_bottom_n",
        "top_and_bottom_n",
        "long_short",
        "rank",
        "ranking",
        "ranked",
        "cross_sectional_rank",
        "cross_sectional_ranking",
        "cross_sectional_ranked",
        "cs_rank",
        "cs_ranking",
        "rank_cross_sectional",
        "top_bottom_quantile",
        "top_and_bottom_quantile",
        "top_bottom_percentile",
        "top_and_bottom_percentile",
        "long_top_short_bottom",
    }:
        return "threshold" if strategy_mode == "time_series" else "top_bottom_n"
    if "top" in token and "bottom" in token:
        return "threshold" if strategy_mode == "time_series" else "top_bottom_n"
    if top_hint and bottom_hint:
        return "threshold" if strategy_mode == "time_series" else "top_bottom_n"
    if top_hint:
        return "threshold" if strategy_mode == "time_series" else "top_n"
    if bottom_hint:
        return "threshold" if strategy_mode == "time_series" else "bottom_n"
    if token.startswith("top_") and any(
        marker in token for marker in ("percent", "pct", "quantile", "bucket")
    ):
        return "threshold" if strategy_mode == "time_series" else "top_n"
    if token.startswith("bottom_") and any(
        marker in token for marker in ("percent", "pct", "quantile", "bucket")
    ):
        return "threshold" if strategy_mode == "time_series" else "bottom_n"
    if token.startswith("top_"):
        return "threshold" if strategy_mode == "time_series" else "top_n"
    if token.startswith("bottom_"):
        return "threshold" if strategy_mode == "time_series" else "bottom_n"
    if token in {
        "threshold",
        "thresholds",
        "all",
        "all_instruments",
        "all_symbols",
        "signal",
        "signals",
        "signal_based",
        "factor_signal",
        "factor_signals",
        "cross_sectional_percentile",
        "cross_sectional_quantile",
        "cs_percentile",
        "cs_quantile",
        "rank_percentile",
        "rank_quantile",
        "cross_sectional_rank_percentile",
        "cross_sectional_rank_quantile",
        "cross_sectional_ranking_percentile",
        "cross_sectional_ranking_quantile",
        "cs_rank_percentile",
        "cs_rank_quantile",
        "cs_ranking_percentile",
        "cs_ranking_quantile",
        "rank_threshold",
        "rank_thresholds",
        "rank_signal_threshold",
        "rank_signal_thresholds",
        "rolling_rank",
        "rolling_ranking",
        "rolling_rank_threshold",
        "rolling_rank_thresholds",
        "rolling_rank_percentile",
        "rolling_rank_quantile",
        "rolling_percentile",
        "rolling_quantile",
        "quantile_threshold",
        "quantile_thresholds",
        "percentile_threshold",
        "percentile_thresholds",
        "cross_sectional_quantile_threshold",
        "cross_sectional_quantile_thresholds",
        "cross_sectional_percentile_threshold",
        "cross_sectional_percentile_thresholds",
        "cs_quantile_threshold",
        "cs_quantile_thresholds",
        "cs_percentile_threshold",
        "cs_percentile_thresholds",
        "cross_sectional_rank_threshold",
        "cross_sectional_rank_thresholds",
        "cs_rank_threshold",
        "cs_rank_thresholds",
        "percentile_rank",
        "quantile_rank",
        "by_threshold",
        "by_thresholds",
        "by_signal_threshold",
        "signal_threshold",
        "signal_thresholds",
        "absolute_threshold",
        "absolute_thresholds",
        "absolute_signal_threshold",
        "absolute_signal_thresholds",
        "signal_percentile",
        "time_series_percentile",
        "time_series_quantile",
        "time_series_top_decile",
        "time_series_bottom_decile",
        "ts_percentile",
        "ts_quantile",
        "ts_top_decile",
        "ts_bottom_decile",
        "absolute_percentile",
        "absolute_quantile",
        "continuous",
        "continuous_signal",
        "continuous_threshold",
        "continuous_signal_threshold",
        "percentile",
        "quantile",
        "zscore",
        "z_score",
    } or _text_contains_any(
        value,
        (
            "\u9608\u503c",
            "\u5206\u4f4d",
            "\u6807\u51c6\u5dee",
            "\u5f53",
            "threshold",
            "quantile",
            "zscore",
            "when",
        ),
    ):
        return "threshold"
    if strategy_mode == "time_series":
        return "threshold"
    return str(value)


def _normalize_rebalance_freq(value: Any) -> str:
    token = _normalized_token(value)
    period_match = re.fullmatch(
        r"(?P<days>\d+)_?(?:trading_?|business_?)?(?:day|days|d|bar|bars)",
        token,
    )
    if period_match:
        days = int(period_match.group("days"))
        if days <= 3:
            return "daily"
        if days <= 10:
            return "weekly"
        return "monthly"
    if token in {"daily", "day", "1d", "d"} or _text_contains_any(
        value, ("\u6bcf\u65e5", "\u65e5\u9891", "daily", "daily_freq")
    ):
        return "daily"
    if token in {
        "weekly",
        "week",
        "1w",
        "w",
        "w_mon",
        "w_tue",
        "w_wed",
        "w_thu",
        "w_fri",
        "w_sat",
        "w_sun",
        "biweek",
        "bi_week",
        "biweekly",
        "bi_weekly",
        "fortnight",
        "fortnightly",
        "2w",
        "2_week",
        "2_weeks",
        "two_week",
        "two_weeks",
    } or _text_contains_any(
        value, ("\u6bcf\u5468", "\u5468\u9891", "\u53cc\u5468", "weekly", "weekly_freq", "biweekly")
    ):
        return "weekly"
    if token in {"monthly", "month", "1m", "m"} or _text_contains_any(
        value, ("\u6bcf\u6708", "\u6708\u9891", "monthly", "monthly_freq")
    ):
        return "monthly"
    return str(value)


# --- Candidate Payload & Config Conversion ---

def normalize_strategy_candidate_payload(
    candidate: Dict[str, Any], state: AlphaMinerState
) -> Dict[str, Any]:
    """Normalize common LLM enum aliases before strict StrategyConfig validation."""
    market_profile = state.get("market_profile", "cn_stock")
    payload = _merge_structured_selection_rule(dict(candidate))
    strategy_mode = _normalize_strategy_mode(
        payload.get("strategy_mode"),
        market_profile,
        payload.get("template_name"),
    )
    selection_text = payload.get("selection_rule")
    direction = _normalize_direction(payload.get("direction"), strategy_mode, selection_text)
    selection_rule = _normalize_selection_rule(selection_text, strategy_mode)
    if strategy_mode == "cross_sectional" and direction == "long_flat":
        direction = "long_only"

    raw_counts = payload.get("counts")
    thresholds = _clean_floats(payload.get("thresholds"))
    quantile_thresholds = _thresholds_from_quantile_counts(raw_counts)
    for key, value in quantile_thresholds.items():
        thresholds.setdefault(key, value)
    counts = _clean_positive_ints(raw_counts)
    holding_constraints = _clean_holding_constraints(payload.get("holding_constraints"))
    cost_model = _clean_cost_model(payload.get("cost_model"))

    if (
        quantile_thresholds
        and selection_rule in {"top_n", "bottom_n", "top_bottom_n"}
        and not any(key in counts for key in ("top_n", "bottom_n"))
    ):
        selection_rule = "threshold"
    if selection_rule not in {"threshold", "top_n", "bottom_n", "top_bottom_n"}:
        if thresholds:
            selection_rule = "threshold"
        elif "top_n" in counts and "bottom_n" in counts:
            selection_rule = "top_bottom_n"
        elif "top_n" in counts:
            selection_rule = "top_n"
        elif "bottom_n" in counts:
            selection_rule = "bottom_n"

    if selection_rule == "threshold":
        if thresholds.get("long_threshold") is None and thresholds.get("short_threshold") is None:
            if direction == "long_short":
                thresholds.setdefault("long_threshold", 0.75)
                thresholds.setdefault("short_threshold", 0.25)
                thresholds.setdefault("exit_threshold", 0.5)
            else:
                thresholds.setdefault("long_threshold", 0.6)
                thresholds.setdefault("exit_threshold", 0.45)
    elif selection_rule == "top_n":
        counts.setdefault("top_n", 20)
    elif selection_rule == "bottom_n":
        counts.setdefault("bottom_n", 20)
    elif selection_rule == "top_bottom_n":
        counts.setdefault("top_n", 20)
        counts.setdefault("bottom_n", 20)

    payload.update(
        {
            "strategy_mode": strategy_mode,
            "direction": direction,
            "selection_rule": selection_rule,
            "rebalance_freq": _normalize_rebalance_freq(
                payload.get("rebalance_freq", "daily")
            ),
            "thresholds": thresholds,
            "counts": counts,
            "holding_constraints": holding_constraints,
            "cost_model": cost_model,
        }
    )
    return payload


def candidate_to_strategy_config(
    candidate: Dict[str, Any], state: AlphaMinerState
) -> Dict[str, Any]:
    """Convert a strategy candidate dict (from agent or critic) into a
    validated StrategyConfig payload. Shared by StrategyAgent and StrategyCritic.

    Raises ValueError / pydantic.ValidationError on bad input — callers must
    decide whether to skip or surface the failure.
    """
    candidate = normalize_strategy_candidate_payload(candidate, state)
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


# --- StrategyAgent Class ---

class StrategyAgent:
    def __init__(
        self,
        provider: str = None,
        model: str = None,
        base_url: str = None,
        reasoning_effort: str = None,
    ):
        self.llm = get_llm(
            temperature=0.2,
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
            "thresholds (dict, e.g. {\"long_threshold\": 0.8, \"short_threshold\": 0.2}), "
            "counts (dict, e.g. {\"top_n\": 100, \"bottom_n\": 50}), "
            "holding_constraints (dict, e.g. {\"max_positions\": 200, \"max_weight_per_position\": 0.02}), "
            "cost_model (dict, e.g. {\"commission_bps\": 5.0, \"slippage_bps\": 2.0}), "
            "rationale (string)."
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
                payload = normalize_strategy_candidate_payload(
                    item.model_dump(mode="json"), state
                )
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
