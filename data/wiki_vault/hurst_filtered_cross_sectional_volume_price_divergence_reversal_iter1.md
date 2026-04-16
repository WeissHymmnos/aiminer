---
title: "Hurst-Filtered Cross-Sectional Volume-Price Divergence Reversal"
slug: "hurst_filtered_cross_sectional_volume_price_divergence_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,42)∈[0.35,0.65], -1, 0)  Sign(Corr(Rank($close/Ref($close,5)),Rank($volume),10))  (Mean($volume,3)/Mean($…"
updated: "2026-04-11T20:46:58.072774"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Cross-Sectional Volume-Price Divergence Reversal

## Summary

Hypothesis: Rank( If(Hurst($close,42)∈[0.35,0.65], -1, 0)  Sign(Corr(Rank($close/Ref($close,5)),Rank($volume),10))  (Mean($volume,3)/Mean($…

## Hypothesis

Hypothesis: Rank( If(Hurst($close,42)∈[0.35,0.65], -1, 0)  Sign(Corr(Rank($close/Ref($close,5)),Rank($volume),10))  (Mean($volume,3)/Mean($…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(GreaterEqual(Ts_Percentile($close,42,50),0.35),LessEqual(Ts_Percentile($close,42,50),0.65)),1,0)*Sign(Corr(Rank(Delta($close,5)),Rank($volume),10))*(Mean($volume,3)/Mean($volume,20)-1))```

**Math Formula**: R_{t}=\text{Rank}\!\left(\;\mathbf{1}_{\left[0.35,\,0.65\right]}\!\bigl(H_{42}(P)\bigr)\;\cdot\;\text{sgn}\!\left(\text{Corr}\!\left(\;\text{Rank}\!\left(\frac{P_{t}}{P_{t-5}}\right),\;\text{Rank}(V_{t}),\;10\;\right)\right)\;\cdot\;\left(\frac{\bar{V}_{3}}{\bar{V}_{20}}-1\right)\;\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
