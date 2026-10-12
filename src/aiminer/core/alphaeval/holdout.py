"""Train / validation / test segmentation for factor evaluation.

The research loop only ever sees train-segment metrics. The validation
segment is used by the manager to confirm a factor before it enters the
pool, and the test (out-of-sample) segment is reported but never used for
selection. Keeping the three windows explicit prevents the full-window IC
from leaking holdout information back into the LLM search.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from aiminer.core.constants import TRADING_DAYS_PER_YEAR

DEFAULT_VALID_SPLIT_DATE = "2021-01-01"
DEFAULT_OOS_SPLIT_DATE = "2023-01-01"
# Calendar fractions used when the default split dates do not fall inside
# the evaluation window: 60% train / 20% validation / 20% test.
_AUTO_VALID_FRACTION = 0.6
_AUTO_OOS_FRACTION = 0.8


def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def resolve_split_dates(
    start_date: str,
    end_date: str,
    valid_split_date: Optional[str] = None,
    oos_split_date: Optional[str] = None,
) -> Tuple[str, str]:
    """Return ``(valid_split_date, oos_split_date)`` for a window.

    Explicit dates are honoured as given (they must be ordered). When a date
    is omitted, the module defaults are used if they fall strictly inside
    ``(start_date, end_date]``; otherwise the window is split 60/20/20 by
    calendar time so every segment is non-empty for reasonable windows.
    """
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if end <= start:
        raise ValueError(
            f"Evaluation window end {end_date} must be after start {start_date}."
        )

    if valid_split_date is not None and oos_split_date is not None:
        valid = pd.Timestamp(valid_split_date)
        oos = pd.Timestamp(oos_split_date)
        if valid > oos:
            raise ValueError(
                f"valid_split_date {valid_split_date} must not be after "
                f"oos_split_date {oos_split_date}."
            )
        return _fmt(valid), _fmt(oos)

    span = end - start
    auto_valid = start + span * _AUTO_VALID_FRACTION
    auto_oos = start + span * _AUTO_OOS_FRACTION

    def _inside(ts: pd.Timestamp) -> bool:
        return start < ts <= end

    if valid_split_date is not None:
        valid = pd.Timestamp(valid_split_date)
        default_oos = pd.Timestamp(DEFAULT_OOS_SPLIT_DATE)
        oos = default_oos if _inside(default_oos) and default_oos > valid else (
            valid + (end - valid) / 2
        )
        return _fmt(valid), _fmt(oos)

    if oos_split_date is not None:
        oos = pd.Timestamp(oos_split_date)
        default_valid = pd.Timestamp(DEFAULT_VALID_SPLIT_DATE)
        valid = (
            default_valid
            if _inside(default_valid) and default_valid < oos
            else start + (oos - start) * 0.75
        )
        return _fmt(valid), _fmt(oos)

    default_valid = pd.Timestamp(DEFAULT_VALID_SPLIT_DATE)
    default_oos = pd.Timestamp(DEFAULT_OOS_SPLIT_DATE)
    if (
        _inside(default_valid)
        and _inside(default_oos)
        and default_valid < default_oos
    ):
        return _fmt(default_valid), _fmt(default_oos)
    return _fmt(auto_valid), _fmt(auto_oos)


def _to_datetime_index(series: pd.Series) -> pd.Series:
    if isinstance(series.index, pd.DatetimeIndex):
        return series
    out = series.copy()
    out.index = pd.to_datetime(out.index, errors="coerce")
    return out[out.index.notna()]


def segment_stats(
    ic_series: pd.Series,
    rank_ic_series: pd.Series,
    daily_returns: pd.Series,
    start: Optional[str],
    end: Optional[str],
    turnover_series: Optional[pd.Series] = None,
    gross_daily_returns: Optional[pd.Series] = None,
) -> Optional[Dict[str, Any]]:
    """Metrics for dates in ``[start, end)``; ``None`` when the slice is empty.

    ``None`` bounds are open. An empty segment never falls back to another
    window's numbers.
    """
    ic_series = _to_datetime_index(ic_series)
    rank_ic_series = _to_datetime_index(rank_ic_series)
    daily_returns = _to_datetime_index(daily_returns)
    if turnover_series is not None:
        turnover_series = _to_datetime_index(turnover_series)
    if gross_daily_returns is not None:
        gross_daily_returns = _to_datetime_index(gross_daily_returns)

    def _mask(index: pd.Index) -> np.ndarray:
        mask = np.ones(len(index), dtype=bool)
        if start is not None:
            mask &= index >= pd.Timestamp(start)
        if end is not None:
            mask &= index < pd.Timestamp(end)
        return mask

    ic = ic_series[_mask(ic_series.index)].dropna()
    if ic.empty:
        return None
    rank_ic = rank_ic_series[_mask(rank_ic_series.index)].dropna()
    rets = daily_returns[_mask(daily_returns.index)].dropna()

    sharpe = None
    max_dd = None
    if len(rets) >= 2:
        sharpe = float(
            rets.mean() / (rets.std() + 1e-8) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
        cum = (1 + rets).cumprod()
        max_dd = float((cum / cum.cummax() - 1).min())

    stats: Dict[str, Any] = {
        "ic": round(float(ic.mean()), 4),
        "rank_ic": (
            round(float(rank_ic.mean()), 4) if not rank_ic.empty else None
        ),
        "sharpe": sharpe,
        "max_dd": max_dd,
        "n_days": int(len(ic)),
    }

    if gross_daily_returns is not None:
        gross_rets = gross_daily_returns[
            _mask(gross_daily_returns.index)
        ].dropna()
        if len(gross_rets) >= 2:
            stats["gross_sharpe"] = float(
                gross_rets.mean()
                / (gross_rets.std() + 1e-8)
                * np.sqrt(TRADING_DAYS_PER_YEAR)
            )
            g_cum = (1 + gross_rets).cumprod()
            stats["gross_max_dd"] = float((g_cum / g_cum.cummax() - 1).min())
        else:
            stats["gross_sharpe"] = None
            stats["gross_max_dd"] = None

    if turnover_series is not None:
        to = turnover_series[_mask(turnover_series.index)].dropna()
        stats["turnover"] = (
            round(float(to.mean()), 4) if not to.empty else None
        )

    return stats
