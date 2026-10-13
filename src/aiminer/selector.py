"""Factor selection, IC culling, orientation, and deduplication logic."""

from __future__ import annotations

from typing import Any
import uuid

from loguru import logger
import numpy as np
import pandas as pd

from aiminer.core.constants import IC_CULL_THRESHOLD

try:
    from aiminer.core.orthogonalization import (
        compute_cross_sectional_factor_correlation,
    )
except ImportError:
    compute_cross_sectional_factor_correlation = None


def _coerce_returns_series(returns: Any) -> pd.Series:
    if isinstance(returns, pd.Series):
        series = returns.copy(deep=False)
    elif isinstance(returns, dict):
        series = pd.Series(returns, dtype=float)
    elif returns is None:
        return pd.Series(dtype=float)
    else:
        try:
            series = pd.Series(returns, dtype=float)
        except Exception:
            return pd.Series(dtype=float)

    if series.empty:
        return pd.Series(dtype=float)

    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index, errors="coerce")
    series = pd.to_numeric(series, errors="coerce")
    valid_mask = series.index.notna() & series.notna()
    if not valid_mask.any():
        return pd.Series(dtype=float)
    return series[valid_mask].sort_index()


def _factor_return_series(factor: dict[str, Any]) -> pd.Series:
    cached = factor.get("_normalized_return_series")
    if isinstance(cached, pd.Series):
        return cached
    series = _coerce_returns_series(
        factor.get("strategy_daily_returns") or factor.get("returns")
    )
    factor["_normalized_return_series"] = series
    return series


def _series_correlation(
    left: pd.Series, right: pd.Series, min_overlap: int = 10
) -> float | None:
    if left is None or right is None or left.empty or right.empty:
        return None

    overlap = left.index.intersection(right.index)
    if len(overlap) < min_overlap:
        return None

    left_aligned = left.reindex(overlap)
    right_aligned = right.reindex(overlap)
    valid_mask = left_aligned.notna() & right_aligned.notna()
    if int(valid_mask.sum()) < min_overlap:
        return None

    corr = left_aligned[valid_mask].corr(right_aligned[valid_mask])
    return float(corr) if pd.notna(corr) else None


def _invert_returns(returns: Any) -> Any:
    if isinstance(returns, pd.Series):
        return -returns
    if isinstance(returns, dict):
        inverted = {}
        for key, value in returns.items():
            try:
                inverted[key] = -float(value)
            except (TypeError, ValueError):
                continue
        return inverted
    if returns is None:
        return returns
    try:
        return -pd.Series(returns, dtype=float)
    except Exception:
        return returns


def _is_simulated_factor(factor: dict[str, Any]) -> bool:
    metrics = factor.get("metrics") or {}
    return bool(factor.get("is_simulated") or metrics.get("_simulated"))


def _orient_negative_ic_factor(
    factor: dict[str, Any], threshold: float
) -> dict[str, Any]:
    perf = float(factor.get("perf_metric", 0.0) or 0.0)
    if perf >= -threshold:
        return factor

    factor["raw_perf_metric"] = perf
    factor["perf_metric"] = abs(perf)
    factor["signal_direction"] = -1
    factor["returns"] = _invert_returns(factor.get("returns"))
    factor.pop("_normalized_return_series", None)

    metrics = dict(factor.get("metrics") or {})
    for key in ("information_coefficient", "ic", "rank_ic"):
        if key in metrics:
            try:
                metrics[f"raw_{key}"] = float(metrics[key])
                metrics[key] = abs(float(metrics[key]))
            except (TypeError, ValueError):
                pass
    if metrics:
        factor["metrics"] = metrics

    selection = factor.get("selection_score")
    try:
        if selection is not None and float(selection) < 0:
            factor["selection_score"] = abs(float(selection))
    except (TypeError, ValueError):
        pass

    return factor


def factor_score(
    factor: dict[str, Any], key: str, default: float = 0.0
) -> float:
    try:
        return float(factor.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def cull_alpha_pool(
    results_list: list[dict[str, Any]],
    threshold: float = IC_CULL_THRESHOLD,
) -> list[dict[str, Any]]:
    """Drop weak or simulated factors whose absolute IC is below threshold."""
    valid_factors = []
    for res in results_list:
        if res.get("error"):
            continue
        if _is_simulated_factor(res):
            continue
        perf = float(res.get("perf_metric", 0.0) or 0.0)
        if perf > threshold:
            valid_factors.append(res)
        elif perf < -threshold:
            valid_factors.append(_orient_negative_ic_factor(res, threshold))
    return valid_factors


def dedupe_alpha_pool_by_returns(
    alpha_pool: list[dict[str, Any]],
    *,
    stage: str = "filter",
    corr_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Deduplicate factors within same market profile if return correlation > corr_threshold."""
    if len(alpha_pool) < 2:
        return list(alpha_pool)

    ordered = sorted(
        alpha_pool,
        key=lambda item: (
            float(item.get("selection_score", float("-inf")) or float("-inf")),
            float(item.get("perf_metric", 0.0) or 0.0),
        ),
        reverse=True,
    )
    final_pool: list[dict[str, Any]] = []
    rejected_ids = set()
    for factor in ordered:
        new_returns = _factor_return_series(factor)
        is_redundant = False
        for existing_factor in final_pool:
            same_market = factor.get("market_profile") == existing_factor.get(
                "market_profile"
            )
            if not same_market:
                continue

            existing_returns = _factor_return_series(existing_factor)
            corr = _series_correlation(new_returns, existing_returns)
            if corr is not None and corr > corr_threshold:
                is_redundant = True
                rejected_ids.add(factor.get("id"))
                logger.info(
                    f"[{stage}:dedupe_correlated_returns] "
                    f"Factor {factor.get('id')} has high correlation "
                    f"({corr:.2f}) with {existing_factor.get('id')}."
                )
                break

            new_fvals = factor.get("factor_series")
            exist_fvals = existing_factor.get("factor_series")
            if (
                compute_cross_sectional_factor_correlation is not None
                and isinstance(new_fvals, pd.Series)
                and isinstance(exist_fvals, pd.Series)
            ):
                f_corr = compute_cross_sectional_factor_correlation(
                    new_fvals, exist_fvals
                )
                if f_corr is not None and f_corr > 0.75:
                    is_redundant = True
                    rejected_ids.add(factor.get("id"))
                    logger.info(
                        f"[{stage}:dedupe_correlated_vals] "
                        f"Factor {factor.get('id')} rank correlation "
                        f"({f_corr:.2f}) with {existing_factor.get('id')}."
                    )
                    break

        if not is_redundant:
            final_pool.append(factor)

    return final_pool
