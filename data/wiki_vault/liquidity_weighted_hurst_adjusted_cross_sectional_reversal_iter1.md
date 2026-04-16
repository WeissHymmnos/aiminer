---
title: "Liquidity-Weighted Hurst-Adjusted Cross-Sectional Reversal"
slug: "liquidity_weighted_hurst_adjusted_cross_sectional_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,14))^2 * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,5)),Rank($volume),7)) ) goes long s…"
updated: "2026-04-14T12:25:25"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Weighted Hurst-Adjusted Cross-Sectional Reversal

## Summary

Rank( (1-Hurst($close,14))^2 * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,5)),Rank($volume),7)) ) goes long s…

## Hypothesis

Rank( (1-Hurst($close,14))^2 * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,5)),Rank($volume),7)) ) goes long s…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Pow(Sub(1, Mean(Ref($close, 1), 14)), 2), Mul(Sign(Delta($close, 3)), Div(Delta($volume, 1), Mean($volume, 20)))), Sub(1, Corr(Rank(Div($close, Ref($close, 5))), Rank($volume), 7)))```

**Math Formula**: R_{i}=\text{Rank}_i\left(\left(1-H_{i,14}\right)^2\cdot\text{sgn}\left(C_{i,t}-C_{i,t-3}\right)\cdot\frac{V_{i,t}-V_{i,t-1}}{\bar{V}_{i,20}}\cdot\left(1-\text{Corr}_7\left(\text{Rank}\left(\frac{C_{i,t}}{C_{i,t-5}}\right),\text{Rank}\left(V_{i,t}\right)\right)\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
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

## Next Steps

Promote or refine after collecting stronger evidence.
