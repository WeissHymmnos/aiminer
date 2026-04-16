---
title: "Intraday Volume-Weighted Return Dispersion Reversal"
slug: "intraday_volume_weighted_return_dispersion_reversal_iter3"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (TsMean($close,5) - TsMean($vwap,5)) / Std($volume,5)  Sign(Corr(Delta($close,3), Delta($volume,3), 10)) ) goes long (sho…"
updated: "2026-04-11T20:47:27.028743"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Intraday Volume-Weighted Return Dispersion Reversal

## Summary

Hypothesis: Rank( (TsMean($close,5) - TsMean($vwap,5)) / Std($volume,5)  Sign(Corr(Delta($close,3), Delta($volume,3), 10)) ) goes long (sho…

## Hypothesis

Hypothesis: Rank( (TsMean($close,5) - TsMean($vwap,5)) / Std($volume,5)  Sign(Corr(Delta($close,3), Delta($volume,3), 10)) ) goes long (sho…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mult(Div(Minus(Mean($close,5),Mean($vwap,5)),Std($volume,5)),Sign(Corr(Delta(Ref($close,3),1),Delta(Ref($volume,3),1),10))))```

**Math Formula**: R = \text{rank}\left( \frac{ \text{mean}_{t=0}^{4}(C_t) - \text{mean}_{t=0}^{4}(V_t) }{ \text{std}_{t=0}^{4}(Q_t) } \cdot \text{sign}\left( \text{corr}_{k=0}^{9}\left( C_{k-3}-C_{k}, Q_{k-3}-Q_{k} \right) \right) \right)

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
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
