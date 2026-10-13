"""Factor orthogonalization and incremental information coefficient (IC) analysis.

Provides tools for detecting multi-collinearity and redundancy among alpha factors:
1. Cross-sectional rank correlation between factor values.
2. Cross-sectional OLS projection & residual computation.
3. Incremental IC: rank correlation of the residual signal with forward returns.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd


def compute_cross_sectional_factor_correlation(
    new_factor_series: pd.Series,
    existing_factor_series: pd.Series,
    min_overlap: int = 10,
) -> Optional[float]:
    """Compute average daily cross-sectional Spearman rank correlation between two factors.

    Both series must have a MultiIndex of (datetime, instrument) or compatible Index.
    """
    if (
        new_factor_series is None
        or existing_factor_series is None
        or new_factor_series.empty
        or existing_factor_series.empty
    ):
        return None

    # Align on common (datetime, instrument)
    joined = pd.concat(
        [
            new_factor_series.rename("new"),
            existing_factor_series.rename("exist"),
        ],
        axis=1,
        join="inner",
    ).dropna()

    if len(joined) < min_overlap:
        return None

    if (
        isinstance(joined.index, pd.MultiIndex)
        and "datetime" in joined.index.names
    ):
        daily_corrs = []
        for _, group in joined.groupby(level="datetime"):
            if (
                len(group) >= 3
                and group["new"].nunique() > 1
                and group["exist"].nunique() > 1
            ):
                r = group["new"].rank().corr(group["exist"].rank())
                if pd.notna(r):
                    daily_corrs.append(r)
        if len(daily_corrs) < 3:
            return None
        return float(np.mean(daily_corrs))

    # Single series fallback
    r = joined["new"].rank().corr(joined["exist"].rank())
    return float(r) if pd.notna(r) else None


def compute_incremental_ic(
    new_factor: pd.Series,
    existing_factors: list[pd.Series],
    labels: pd.Series,
    min_obs: int = 20,
) -> Tuple[Optional[float], Optional[float]]:
    """Calculate the incremental (residual) IC of a new factor after orthogonalizing
    against existing factors in the pool.

    Model:
        F_new(t, i) = alpha(t) + sum_k beta_k(t) * F_existing_k(t, i) + epsilon(t, i)

    Returns:
        (incremental_ic, raw_ic):
            - incremental_ic: average rank correlation of epsilon with label
            - raw_ic: average rank correlation of raw F_new with label
    """
    if new_factor is None or labels is None or new_factor.empty or labels.empty:
        return None, None

    if not existing_factors:
        # No existing factors to orthogonalize against: incremental IC equals raw IC
        aligned = pd.concat(
            [new_factor.rename("f"), labels.rename("l")], axis=1, join="inner"
        ).dropna()
        if len(aligned) < min_obs:
            return None, None
        if (
            isinstance(aligned.index, pd.MultiIndex)
            and "datetime" in aligned.index.names
        ):
            ic_series = (
                aligned.groupby(level="datetime")
                .apply(lambda x: x["f"].rank().corr(x["l"].rank()))
                .dropna()
            )
            return (
                (float(ic_series.mean()), float(ic_series.mean()))
                if not ic_series.empty
                else (None, None)
            )
        r = float(aligned["f"].rank().corr(aligned["l"].rank()))
        return r, r

    # Combine all series
    frames = [new_factor.rename("target"), labels.rename("label")]
    for idx, ef in enumerate(existing_factors):
        frames.append(ef.rename(f"base_{idx}"))

    df = pd.concat(frames, axis=1, join="inner").dropna()
    if len(df) < min_obs:
        return None, None

    is_multi = (
        isinstance(df.index, pd.MultiIndex) and "datetime" in df.index.names
    )
    base_cols = [c for c in df.columns if c.startswith("base_")]

    if not is_multi:
        # Cross-sectional flat OLS
        X = df[base_cols].to_numpy()
        X = np.column_stack([np.ones(len(X)), X])
        y = df["target"].to_numpy()
        try:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            residual = y - X @ beta
            inc_ic = float(
                pd.Series(residual)
                .rank()
                .corr(df["label"].reset_index(drop=True).rank())
            )
            raw_ic = float(df["target"].rank().corr(df["label"].rank()))
            return inc_ic, raw_ic
        except Exception:
            return None, None

    # Daily cross-sectional regression
    inc_ics = []
    raw_ics = []
    for _, group in df.groupby(level="datetime"):
        if len(group) <= len(base_cols) + 2:
            continue
        y = group["target"].to_numpy()
        X = group[base_cols].to_numpy()
        X = np.column_stack([np.ones(len(X)), X])
        l = group["label"].to_numpy()

        try:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            res = y - X @ beta
            if np.std(res) > 1e-12 and np.std(l) > 1e-12:
                r_inc = float(pd.Series(res).rank().corr(pd.Series(l).rank()))
                r_raw = float(
                    group["target"].rank().corr(group["label"].rank())
                )
                if pd.notna(r_inc):
                    inc_ics.append(r_inc)
                if pd.notna(r_raw):
                    raw_ics.append(r_raw)
        except Exception:
            continue

    if not inc_ics:
        return None, None

    return float(np.mean(inc_ics)), float(np.mean(raw_ics))
