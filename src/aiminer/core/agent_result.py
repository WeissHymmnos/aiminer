from __future__ import annotations

from typing import Any

import pandas as pd


def compact_returns(daily_returns_dict) -> dict:
    if not daily_returns_dict:
        return {}

    series = pd.Series(daily_returns_dict)
    if series.empty:
        return {}

    series.index = pd.to_datetime(series.index, errors="coerce")
    series = pd.to_numeric(series, errors="coerce")
    valid_mask = series.index.notna() & series.notna()
    if not valid_mask.any():
        return {}

    series = series[valid_mask].sort_index()
    compact = {}
    for idx, value in series.items():
        key = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
        compact[key] = float(value)
    return compact


def factor_result_view(final_state: dict) -> dict:
    snapshot = final_state.get("best_factor_snapshot") or {}
    if not snapshot:
        snapshot = {
            "iteration": final_state.get("iteration"),
            "hypothesis": final_state.get("hypothesis_name"),
            "hypothesis_name": final_state.get("hypothesis_name"),
            "hypothesis_description": final_state.get("hypothesis_description"),
            "code": final_state.get("code_expression"),
            "code_expression": final_state.get("code_expression"),
            "metrics": final_state.get("backtest_metrics", {}) or {},
            "returns": final_state.get("daily_returns", {}) or {},
            "daily_returns": final_state.get("daily_returns", {}) or {},
            "plot_paths": final_state.get("plot_paths", {}) or {},
            "is_effective": final_state.get("is_effective", False),
            "is_simulated": final_state.get("is_simulated", False),
            "ic_direction": final_state.get("ic_direction"),
            "ic_direction_label": final_state.get("ic_direction_label"),
        }

    return {
        "iteration": snapshot.get("iteration", final_state.get("iteration")),
        "hypothesis": snapshot.get("hypothesis") or snapshot.get("hypothesis_name"),
        "code": snapshot.get("code") or snapshot.get("code_expression"),
        "metrics": snapshot.get("metrics")
        or snapshot.get("backtest_metrics")
        or final_state.get("backtest_metrics", {})
        or {},
        "returns": snapshot.get("returns")
        or snapshot.get("daily_returns")
        or final_state.get("daily_returns", {})
        or {},
        "plot_paths": snapshot.get("plot_paths")
        or final_state.get("plot_paths", {})
        or {},
        "strategy_candidates": snapshot.get(
            "strategy_candidates", final_state.get("strategy_candidates", [])
        ),
        "strategy_results": snapshot.get(
            "strategy_results", final_state.get("strategy_results", [])
        ),
        "best_strategy_result": snapshot.get(
            "best_strategy_result", final_state.get("best_strategy_result")
        ),
        "best_strategy_config": snapshot.get(
            "best_strategy_config", final_state.get("best_strategy_config")
        ),
        "best_strategy_metrics": snapshot.get(
            "best_strategy_metrics", final_state.get("best_strategy_metrics")
        ),
        "best_strategy_id": snapshot.get(
            "best_strategy_id", final_state.get("best_strategy_id")
        ),
        "strategy_daily_returns": snapshot.get(
            "strategy_daily_returns", final_state.get("strategy_daily_returns", {})
        ),
        "selection_score": snapshot.get(
            "selection_score", final_state.get("selection_score", 0.0)
        ),
        "execution_style": snapshot.get(
            "execution_style", final_state.get("execution_style")
        ),
        "strategy_failure_reason": snapshot.get(
            "strategy_failure_reason", final_state.get("strategy_failure_reason")
        ),
        "is_effective": snapshot.get(
            "is_effective", final_state.get("is_effective", False)
        ),
        "is_simulated": snapshot.get(
            "is_simulated", final_state.get("is_simulated", False)
        ),
        "ic_direction": snapshot.get("ic_direction", final_state.get("ic_direction")),
        "ic_direction_label": snapshot.get(
            "ic_direction_label", final_state.get("ic_direction_label")
        ),
    }


def state_to_agent_result(
    final_state: dict,
    *,
    settings: Any | None = None,
    role_prompt: str | None = None,
    run_id: str | None = None,
    agent_id: str | None = None,
    max_iterations: int | None = None,
) -> dict:
    factor_view = factor_result_view(final_state)
    metrics = factor_view["metrics"] or {}
    perf_metric = float(metrics.get("information_coefficient", 0.0) or 0.0)
    terminal_error = final_state.get("error")
    has_recoverable_best = bool(
        final_state.get("best_factor_snapshot") and factor_view.get("code") and metrics
    )

    return {
        "run_id": run_id or final_state.get("run_id"),
        "agent_id": agent_id or final_state.get("agent_id"),
        "iteration": factor_view.get(
            "iteration", final_state.get("iteration", max_iterations)
        ),
        "evaluation_mode": (
            getattr(settings, "evaluation_mode", None)
            or final_state.get("evaluation_mode")
        ),
        "evaluation_engine": (
            getattr(settings, "evaluation_engine", None)
            or final_state.get("evaluation_engine")
        ),
        "llm_provider": getattr(settings, "llm_provider", None)
        or final_state.get("llm_provider"),
        "llm_model": getattr(settings, "llm_model", None) or final_state.get("llm_model"),
        "llm_base_url": getattr(settings, "llm_base_url", None)
        or final_state.get("llm_base_url"),
        "llm_reasoning_effort": getattr(settings, "llm_reasoning_effort", None)
        or final_state.get("llm_reasoning_effort"),
        "data_backend": (
            getattr(settings, "data_backend", None) or final_state.get("data_backend")
        ),
        "market_mode": (
            getattr(settings, "market_mode", None) or final_state.get("market_mode")
        ),
        "market_profile": (
            getattr(settings, "market_profile", None)
            or final_state.get("market_profile")
        ),
        "market_profiles": (
            getattr(settings, "market_profiles", None)
            or final_state.get("market_profiles")
        ),
        "role": role_prompt or final_state.get("role_prompt"),
        "hypothesis": factor_view.get("hypothesis"),
        "code": factor_view.get("code"),
        "metrics": metrics,
        "perf_metric": perf_metric,
        "returns": compact_returns(factor_view.get("returns")),
        "plot_paths": factor_view.get("plot_paths", {}),
        "strategy_candidates": factor_view.get("strategy_candidates", []),
        "strategy_results": factor_view.get("strategy_results", []),
        "best_strategy_result": factor_view.get("best_strategy_result"),
        "best_strategy_config": factor_view.get("best_strategy_config"),
        "best_strategy_metrics": factor_view.get("best_strategy_metrics"),
        "best_strategy_id": factor_view.get("best_strategy_id"),
        "strategy_daily_returns": factor_view.get("strategy_daily_returns", {}),
        "selection_score": factor_view.get("selection_score", 0.0),
        "execution_style": factor_view.get("execution_style"),
        "strategy_failure_reason": factor_view.get("strategy_failure_reason"),
        "is_effective": factor_view.get("is_effective", False),
        "is_simulated": factor_view.get("is_simulated", False),
        "ic_direction": factor_view.get("ic_direction"),
        "ic_direction_label": factor_view.get("ic_direction_label"),
        "terminal_error": terminal_error if has_recoverable_best else None,
        "error": None if has_recoverable_best else terminal_error,
    }
