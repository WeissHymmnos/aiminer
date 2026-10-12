"""Genetic crossover logic for recombining high-performing alpha factors."""

from __future__ import annotations

from typing import Any, Callable, Optional
import uuid

from loguru import logger

from aiminer.scheduler import run_agent_task
from aiminer.selector import (
    _coerce_returns_series,
    _factor_return_series,
    _is_simulated_factor,
    _series_correlation,
    factor_score,
)

CROSSOVER_ROLE = "遗传交叉"


def select_crossover_parents(
    factors: list[dict[str, Any]],
    score_fn: Optional[Callable[[dict[str, Any], str], float]] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select the two best-performing factors as parents for crossover."""
    if len(factors) < 2:
        raise ValueError(
            "At least two factors are required for genetic crossover."
        )
    fn = score_fn or factor_score
    ranked = sorted(
        factors,
        key=lambda item: fn(item, "perf_metric"),
        reverse=True,
    )
    return ranked[0], ranked[1]


def build_crossover_role(
    top1: dict[str, Any],
    top2: dict[str, Any],
    score_fn: Optional[Callable[[dict[str, Any], str], float]] = None,
) -> str:
    """Construct LLM system prompt instructing crossover synthesis."""
    fn = score_fn or factor_score
    ic1 = fn(top1, "perf_metric")
    ic2 = fn(top2, "perf_metric")
    return (
        "You are an AI Genetic Crossover Expert. Your task is to combine "
        "two high-performing alpha factors into a single, superior hybrid "
        "factor. You excel at extracting orthogonal components and merging "
        "them logically.\n"
        "Here are the two parent factors:\n"
        f"Parent 1 (IC: {ic1:.4f}): {top1.get('hypothesis') or 'N/A'}\n"
        f"Code: {top1.get('code') or 'N/A'}\n\n"
        f"Parent 2 (IC: {ic2:.4f}): {top2.get('hypothesis') or 'N/A'}\n"
        f"Code: {top2.get('code') or 'N/A'}\n\n"
        "Extract the best ideas from both and synthesize a new Alpha factor."
    )


def run_crossover_agent(
    top1: dict[str, Any],
    top2: dict[str, Any],
    *,
    run_id: str,
    kwargs: dict[str, Any],
    iterations: Optional[int] = None,
    agent_id: str = "agent_crossover",
    score_fn: Optional[Callable[[dict[str, Any], str], float]] = None,
    run_task_fn: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Execute a single crossover agent trial."""
    logger.info("Spawning Crossover Agent...")
    crossover_kwargs = dict(kwargs)
    crossover_kwargs["role_prompt"] = build_crossover_role(
        top1, top2, score_fn=score_fn
    )
    crossover_kwargs["run_id"] = run_id
    crossover_kwargs["agent_id"] = agent_id
    if iterations is not None:
        crossover_kwargs["max_iterations"] = iterations
    runner = run_task_fn or run_agent_task
    result = runner(crossover_kwargs)
    if isinstance(result, dict):
        result["role"] = CROSSOVER_ROLE
    return result


def accept_crossover_result(
    crossover_result: dict[str, Any],
    *,
    comparison_pool: Optional[list[dict[str, Any]]] = None,
    threshold: float = 0.01,
    score_fn: Optional[Callable[[dict[str, Any], str], float]] = None,
) -> tuple[bool, str]:
    """Validate whether hybrid crossover factor passes performance and correlation checks."""
    fn = score_fn or factor_score
    if crossover_result.get("error"):
        return False, "errored"
    if _is_simulated_factor(crossover_result):
        return False, "simulated"
    if fn(crossover_result, "perf_metric") <= threshold:
        return False, "threshold"

    new_returns = _coerce_returns_series(crossover_result.get("returns"))
    if not new_returns.empty and comparison_pool:
        for existing_factor in comparison_pool:
            existing_returns = _factor_return_series(existing_factor)
            if existing_returns.empty:
                continue
            corr = _series_correlation(new_returns, existing_returns)
            if corr is not None and corr > 0.7:
                return False, "correlated"

    crossover_result["id"] = (
        crossover_result.get("id") or f"alpha_{uuid.uuid4().hex[:8]}"
    )
    return True, "accepted"
