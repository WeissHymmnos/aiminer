---
title: "Over-night Gamma-hedge Reversal in High-Skew Names"
slug: "over_night_gamma_hedge_reversal_in_high_skew_names_iter3"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Rank( If($skew20>80Percentile, -1$gap, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),3))  (Std($volume,2)/Std($volume,…"
updated: "2026-04-11T20:50:40.244076"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Over-night Gamma-hedge Reversal in High-Skew Names

## Summary

Hypothesis: Rank( If($skew20>80Percentile, -1$gap, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),3))  (Std($volume,2)/Std($volume,…

## Hypothesis

Hypothesis: Rank( If($skew20>80Percentile, -1$gap, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),3))  (Std($volume,2)/Std($volume,…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(Greater(Ts_Percentile($close, 20, 50), Ts_Percentile($close, 20, 80)), -Delta($open, 1)/Ref($close, 1), 0) * Sign(Corr(Rank($close/Ref($close, 1)), Rank($volume), 3)) * (Std($volume, 2)/Std($volume, 10) - 1))```

**Math Formula**: R_{t}=\operatorname{Rank}\left(\left[\mathbb{1}_{\operatorname{skew}_{20,t}>\Phi_{80,t}^{\operatorname{skew}}}\cdot(-g_{t})\right]\cdot\operatorname{sign}\left(\operatorname{Corr}\left(\operatorname{Rank}\left(\frac{p_{t}}{p_{t-1}}\right),\operatorname{Rank}(v_{t}),3\right)\right)\cdot\left(\frac{\sigma_{v,t,2}}{\sigma_{v,t,10}}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
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
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
