---
title: "Volume-Accelerated Cross-Sectional Reversal"
slug: "volume_accelerated_cross_sectional_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( If(Corr(Rank($volume),Rank($close/Ref($close,1)),3) < -0.4, -1, 1)  (Mean($volume,3)/Mean($volume,15)-1)  TsRank($close-M…"
updated: "2026-04-11T20:50:29.482110"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Volume-Accelerated Cross-Sectional Reversal

## Summary

Hypothesis: Rank( If(Corr(Rank($volume),Rank($close/Ref($close,1)),3) < -0.4, -1, 1)  (Mean($volume,3)/Mean($volume,15)-1)  TsRank($close-M…

## Hypothesis

Hypothesis: Rank( If(Corr(Rank($volume),Rank($close/Ref($close,1)),3) < -0.4, -1, 1)  (Mean($volume,3)/Mean($volume,15)-1)  TsRank($close-M…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(Less(Corr(CSRank($volume), CSRank($close / Ref($close, 1)), 3), -0.4), -1, 1) * (Mean($volume, 3) / Mean($volume, 15) - 1) * Ts_Rank($close - Mean($close, 10), 5))```

**Math Formula**: \text{Signal}_i = \text{Rank}\left[ \; \mathbf{1}\!\left\{\text{Corr}_{t,3}\!\left(\text{Rank}(V_i),\;\text{Rank}\!\left(\frac{C_i}{C_{i,t-1}}\right)\right) < -0.4\right\} \cdot (-1) \;+\; \mathbf{1}\!\left\{\text{Corr}_{t,3}\!\left(\text{Rank}(V_i),\;\text{Rank}\!\left(\frac{C_i}{C_{i,t-1}}\right)\right) \geq -0.4\right\} \cdot 1 \;\right] \;\times\; \left(\frac{\frac{1}{3}\sum_{k=0}^{2}V_{i,t-k}}{\frac{1}{15}\sum_{k=0}^{14}V_{i,t-k}} - 1\right) \;\times\; \text{TS-Rank}_{t,5}\!\left(C_i - \frac{1}{10}\sum_{k=0}^{9}C_{i,t-k}\right)

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
