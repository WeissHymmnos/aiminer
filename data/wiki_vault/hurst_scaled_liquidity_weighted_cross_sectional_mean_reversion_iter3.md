---
title: "Hurst-Scaled Liquidity-Weighted Cross-Sectional Mean-Reversion"
slug: "hurst_scaled_liquidity_weighted_cross_sectional_mean_reversion_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,24)) * Rank(Delta($close,1)) * (1-Corr(Rank($volume),Rank($close),7)) * ($volume/Mean($volume,20)-1) ) goes long the stocks with the most…"
updated: "2026-04-14T12:16:21"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0014"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Scaled Liquidity-Weighted Cross-Sectional Mean-Reversion

## Summary

Rank( (1-Hurst($close,24)) * Rank(Delta($close,1)) * (1-Corr(Rank($volume),Rank($close),7)) * ($volume/Mean($volume,20)-1) ) goes long the stocks with the most…

## Hypothesis

Rank( (1-Hurst($close,24)) * Rank(Delta($close,1)) * (1-Corr(Rank($volume),Rank($close),7)) * ($volume/Mean($volume,20)-1) ) goes long the stocks with the most…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Multiply(Sub(1, Ts_Rank($close, 24)), Rank(Delta($close, 1))), Sub(1, Corr(Rank($volume), Rank($close), 7))), Sub(Div($volume, Mean($volume, 20)), 1)))```

**Math Formula**: R_{i,t}=\operatorname{Rank}_t\left(\left[1-H_{i,t}(24)\right]\cdot\operatorname{Rank}_t\left(\Delta C_{i,t}(1)\right)\cdot\left[1-\rho_{i,t}\left(\operatorname{Rank}_t(V_{i,t}),\operatorname{Rank}_t(C_{i,t}),7\right)\right]\cdot\left(\frac{V_{i,t}}{\bar{V}_{i,t}(20)}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0014 / 0.0000
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
