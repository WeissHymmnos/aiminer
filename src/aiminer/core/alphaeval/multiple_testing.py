"""Deflated Sharpe Ratio (DSR) & Probabilistic Sharpe Ratio (PSR).

Implementation of Bailey & López de Prado (2014) multiple testing
adjustments for strategy and factor evaluation:
  - Expected maximum Sharpe ratio under the null hypothesis.
  - Probabilistic Sharpe Ratio (PSR) accounting for skewness and kurtosis.
  - Deflated Sharpe Ratio (DSR) deflating the benchmark for selection bias.
  - Holm-Bonferroni step-down correction for family-wise error rate control.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
import scipy.stats

EULER_MASCHERONI: float = 0.5772156649015328606


def expected_max_sharpe(
    n_trials: int,
    method: str = "bailey_prado",
) -> float:
    """Expected maximum Sharpe ratio under null hypothesis of N trials.

    Parameters
    ----------
    n_trials:
        Number of independent backtest trials (N).
    method:
        "bailey_prado" (default) or "extreme_value".

    Returns
    -------
    float:
        Expected maximum Sharpe ratio E[max_N] (>= 0.0).
    """
    if n_trials <= 1:
        return 0.0

    n = float(n_trials)
    if method == "extreme_value":
        log_n = float(np.log(n))
        denom = 2.0 * float(np.sqrt(2.0 * log_n))
        num = float(
            np.log(log_n) + np.log(4.0 * np.pi) - 2.0 * EULER_MASCHERONI
        )
        return float(np.sqrt(2.0 * log_n) + num / denom)

    # Standard Bailey & López de Prado (2014) equation (8)
    q1 = float(scipy.stats.norm.ppf(1.0 - 1.0 / n))
    q2 = float(scipy.stats.norm.ppf(1.0 - 1.0 / (n * math.e)))
    return float((1.0 - EULER_MASCHERONI) * q1 + EULER_MASCHERONI * q2)


def probabilistic_sharpe_ratio(
    estimated_sharpe: float,
    sr_benchmark: float = 0.0,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    sample_length: int = 252,
) -> float:
    """Calculate the Probabilistic Sharpe Ratio (PSR).

    Parameters
    ----------
    estimated_sharpe:
        Estimated Sharpe ratio of the factor / strategy.
    sr_benchmark:
        Benchmark Sharpe ratio (default 0.0).
    skewness:
        Return skewness (default 0.0 for normal distribution).
    kurtosis:
        Return Pearson kurtosis (default 3.0 for normal distribution).
    sample_length:
        Sample length T (number of return observations, default 252).

    Returns
    -------
    float:
        PSR value in [0.0, 1.0], representing P(SR > sr_benchmark).
    """
    if estimated_sharpe is None or math.isnan(estimated_sharpe):
        return float("nan")

    sr = float(estimated_sharpe)
    bench = float(sr_benchmark)
    t = max(int(sample_length), 2)
    kurt = max(float(kurtosis), 1.0)
    denom_var = 1.0 - float(skewness) * sr + ((kurt - 1.0) / 4.0) * (sr**2)
    denom = math.sqrt(max(denom_var, 1e-12))
    z = (sr - bench) * math.sqrt(t - 1) / denom
    return float(scipy.stats.norm.cdf(z))


def deflated_sharpe_ratio(
    estimated_sharpe: float,
    var_sharpe_or_trials: Any = 0.0,
    n_trials: int | None = None,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    sample_length: int = 252,
) -> float:
    """Calculate the Deflated Sharpe Ratio (DSR).

    Adjusts the benchmark Sharpe ratio upward according to the number of
    trials N and the variance of trial Sharpe ratios:
        SR_benchmark = E[max_N] * standard_deviation(trials_sharpe)
        DSR = PSR(estimated_sharpe, SR_benchmark)

    Parameters
    ----------
    estimated_sharpe:
        Estimated Sharpe ratio to evaluate.
    var_sharpe_or_trials:
        Either a float (variance of trial Sharpe ratios) or a sequence/array
        of trial Sharpe ratios from evaluated candidates.
    n_trials:
        Number of trials evaluated. If None and var_sharpe_or_trials is a
        sequence, defaults to len(var_sharpe_or_trials).
    skewness:
        Return distribution skewness (default 0.0).
    kurtosis:
        Return distribution Pearson kurtosis (default 3.0).
    sample_length:
        Number of return observations (default 252).

    Returns
    -------
    float:
        Deflated Sharpe Ratio in [0.0, 1.0].
    """
    if estimated_sharpe is None or math.isnan(estimated_sharpe):
        return float("nan")

    if hasattr(var_sharpe_or_trials, "__iter__") and not isinstance(
        var_sharpe_or_trials, (str, bytes)
    ):
        try:
            trials = np.asarray(var_sharpe_or_trials, dtype=float)
            trials = trials[np.isfinite(trials)]
        except (ValueError, TypeError):
            trials = np.array([], dtype=float)
        if len(trials) > 1:
            std_sharpe = float(np.std(trials, ddof=1))
        else:
            std_sharpe = 0.0
        if n_trials is None or n_trials <= 0:
            n_trials = max(len(trials), 1)
    else:
        var = (
            float(var_sharpe_or_trials)
            if var_sharpe_or_trials is not None
            else 0.0
        )
        std_sharpe = math.sqrt(max(var, 0.0))
        if n_trials is None or n_trials <= 0:
            n_trials = 1

    e_max = expected_max_sharpe(n_trials)
    sr_benchmark = e_max * std_sharpe

    return probabilistic_sharpe_ratio(
        estimated_sharpe=estimated_sharpe,
        sr_benchmark=sr_benchmark,
        skewness=skewness,
        kurtosis=kurtosis,
        sample_length=sample_length,
    )


def adjust_pvalues_holm(
    p_values: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Calculate Holm-Bonferroni adjusted p-values.

    Step-down procedure controlling Family-Wise Error Rate (FWER):
        p'_(k) = min(p_(k) * (m - k + 1), 1.0)
        p_adj_(k) = max(p_adj_(k-1), p'_(k))

    Parameters
    ----------
    p_values:
        1D sequence or numpy array of raw p-values.

    Returns
    -------
    np.ndarray:
        1D array of adjusted p-values in the original input order.
    """
    p = np.asarray(p_values, dtype=float)
    if p.size == 0:
        return np.array([], dtype=float)
    if p.size == 1:
        return np.clip(p, 0.0, 1.0)

    n = len(p)
    order = np.argsort(p)
    sorted_p = p[order]

    adj = np.empty(n, dtype=float)
    running_max = 0.0
    for k in range(n):
        val = float(sorted_p[k]) * float(n - k)
        val = min(max(val, 0.0), 1.0)
        running_max = max(running_max, val)
        adj[k] = min(running_max, 1.0)

    out = np.empty(n, dtype=float)
    out[order] = adj
    return out


def holm_bonferroni(
    p_values: Sequence[float] | np.ndarray,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Perform Holm-Bonferroni correction and hypothesis rejection.

    Parameters
    ----------
    p_values:
        1D sequence or numpy array of raw p-values.
    alpha:
        Target family-wise significance level (default 0.05).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]:
        (adjusted_p_values, reject_flags)
    """
    adj = adjust_pvalues_holm(p_values)
    reject = adj <= float(alpha)
    return adj, reject


def select_factors_holm(
    factors: list[dict[str, Any]],
    alpha: float = 0.05,
    p_value_key: str = "p_value",
) -> list[dict[str, Any]]:
    """Filter factor candidates using Holm-Bonferroni adjusted p-values.

    Parameters
    ----------
    factors:
        List of factor dictionaries.
    alpha:
        Significance level threshold (default 0.05).
    p_value_key:
        Key name containing raw p-values in each factor dictionary.

    Returns
    -------
    list[dict[str, Any]]:
        List of factors that reject the null hypothesis at level alpha.
    """
    if not factors:
        return []

    p_vals: list[float] = []
    for factor in factors:
        p = factor.get(p_value_key)
        if p is None:
            # Fallback: estimate two-sided p-value from IC or Sharpe if present
            ic = factor.get("perf_metric") or factor.get("metrics", {}).get(
                "information_coefficient", 0.0
            )
            # Standard normal approximation under H0: IC = 0, N ~ 252
            z = abs(float(ic or 0.0)) * math.sqrt(252.0)
            p = float(2.0 * (1.0 - scipy.stats.norm.cdf(z)))
        p_vals.append(float(p))

    adj, reject = holm_bonferroni(p_vals, alpha=alpha)
    selected: list[dict[str, Any]] = []
    for factor, adj_p, rej in zip(factors, adj, reject):
        factor_copy = dict(factor)
        factor_copy["p_value_holm"] = float(adj_p)
        if rej:
            selected.append(factor_copy)
    return selected
