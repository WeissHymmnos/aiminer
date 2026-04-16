---
title: "Hurst-Scaled Liquidity-Adjusted Intraday Reversal"
slug: "hurst_scaled_liquidity_adjusted_intraday_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,21)) * Delta($close,1) * (1-Corr($volume,$close,5)) * (Mean($volume,3)/Mean($volume,15)-1) ) goes long stocks whose 1-day return is negat…"
updated: "2026-04-14T12:15:28"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0048"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Scaled Liquidity-Adjusted Intraday Reversal

## Summary

Rank( (1-Hurst($close,21)) * Delta($close,1) * (1-Corr($volume,$close,5)) * (Mean($volume,3)/Mean($volume,15)-1) ) goes long stocks whose 1-day return is negat…

## Hypothesis

Rank( (1-Hurst($close,21)) * Delta($close,1) * (1-Corr($volume,$close,5)) * (Mean($volume,3)/Mean($volume,15)-1) ) goes long stocks whose 1-day return is negat…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Multiply(Sub(1, Ts_Rank($close, 21)), Delta($close, 1)), Sub(1, Corr($volume, $close, 5))), Sub(Div(Mean($volume, 3), Mean($volume, 15)), 1)))```

**Math Formula**: R_{i,t}=\text{rank}_t\left(\left(1-H_{i,t}^{(21)}\right)\cdot\Delta C_{i,t}^{(1)}\cdot\left(1-\rho_{i,t}^{(V,C,5)}\right)\cdot\left(\frac{\bar{V}_{i,t}^{(3)}}{\bar{V}_{i,t}^{(15)}}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0048 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
