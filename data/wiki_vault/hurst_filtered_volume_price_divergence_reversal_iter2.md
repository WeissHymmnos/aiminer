---
title: "Hurst-Filtered Volume-Price Divergence Reversal"
slug: "hurst_filtered_volume_price_divergence_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,42)<0.4, -1, 0)  Sign(Delta($close,3))  (1 - Corr(Rank($close/Ref($close,5)),Rank($volume),15))  TsRank($…"
updated: "2026-04-11T20:47:15.217030"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Filtered Volume-Price Divergence Reversal

## Summary

Hypothesis: Rank( If(Hurst($close,42)<0.4, -1, 0)  Sign(Delta($close,3))  (1 - Corr(Rank($close/Ref($close,5)),Rank($volume),15))  TsRank($…

## Hypothesis

Hypothesis: Rank( If(Hurst($close,42)<0.4, -1, 0)  Sign(Delta($close,3))  (1 - Corr(Rank($close/Ref($close,5)),Rank($volume),15))  TsRank($…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(Less(Ts_Rank($close,42),0.4),Mult(-1,Mult(Sign(Delta($close,3)),Mult(Sub(1,Corr(CSRank(Delta($close,5)),CSRank($volume),15)),Ts_Rank($volume,10)))),0))```

**Math Formula**: R_{i,t}=\text{Rank}_t\Bigl(\,\mathbb{1}_{\{H_{i,t}^{(42)}<0.4\}}\cdot(-1)\cdot\text{sgn}\bigl(C_{i,t}-C_{i,t-3}\bigr)\cdot\bigl[1-\rho_{i,t}^{(15)}\bigr]\cdot Q_{i,t}^{V}\bigl(10\bigr)\Bigr)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
