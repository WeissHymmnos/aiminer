---
title: "Liquidity-Adjusted Hurst-Slope Dispersion Reversal"
slug: "liquidity_adjusted_hurst_slope_dispersion_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( (1 - Hurst($close,30)) * (Slope($close,5) - Median(Slope($close,5), 500)) * (1 - Corr($volume, $close, 3)) * ($volume / Ts_Mean($volume,20) - 1) ) goes l…"
updated: "2026-04-14T12:25:51"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.006"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Hurst-Slope Dispersion Reversal

## Summary

Rank( (1 - Hurst($close,30)) * (Slope($close,5) - Median(Slope($close,5), 500)) * (1 - Corr($volume, $close, 3)) * ($volume / Ts_Mean($volume,20) - 1) ) goes l…

## Hypothesis

Rank( (1 - Hurst($close,30)) * (Slope($close,5) - Median(Slope($close,5), 500)) * (1 - Corr($volume, $close, 3)) * ($volume / Ts_Mean($volume,20) - 1) ) goes l…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 30)), Sub(Delta($close, 5), CSRank(Delta($close, 5)))), Sub(1, Corr($volume, $close, 3))), Sub(Div($volume, Mean($volume, 20)), 1)))```

**Math Formula**: R_{i}=\text{Rank}_{i}\left(\left(1-H_{i,30}\right)\cdot\left(S_{i,5}-\widetilde{S}_{\bullet,5,500}\right)\cdot\left(1-C_{i,3}^{(v,p)}\right)\cdot\left(\frac{V_{i}}{\bar{V}_{i,20}}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0060 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
