---
title: "Intraday Volume-Weighted Return Dispersion Reversal"
slug: "intraday_volume_weighted_return_dispersion_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (TsMean($close,3) - TsMean($vwap,3)) / Std($volume,5)  Sign(Corr(Delta($close,1), Delta($volume,1),10)) ) goes long (shor…"
updated: "2026-04-11T20:47:13.121238"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Intraday Volume-Weighted Return Dispersion Reversal

## Summary

Hypothesis: Rank( (TsMean($close,3) - TsMean($vwap,3)) / Std($volume,5)  Sign(Corr(Delta($close,1), Delta($volume,1),10)) ) goes long (shor…

## Hypothesis

Hypothesis: Rank( (TsMean($close,3) - TsMean($vwap,3)) / Std($volume,5)  Sign(Corr(Delta($close,1), Delta($volume,1),10)) ) goes long (shor…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Div(Mean($close,3)-Mean($vwap,3),Std($volume,5))*Sign(Corr(Delta(Ref($close,1),1),Delta(Ref($volume,1),1),10)))```

**Math Formula**: R_{i,t}=\operatorname{rank}_i\left(\frac{\operatorname{TsMean}(C_{i,t},3)-\operatorname{TsMean}(VWAP_{i,t},3)}{\operatorname{Std}(VOL_{i,t},5)}\cdot\operatorname{sign}\left(\operatorname{Corr}\left(\Delta C_{i,t-1,1},\Delta VOL_{i,t-1,1},10\right)\right)\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
