---
title: "Volatility-Adjusted Cross-Sectional Volume Reversal"
slug: "volatility_adjusted_cross_sectional_volume_reversal_iter3"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( -Sign(Delta($close,1))  Power(Std($close,5),0.5)  Corr(Rank($close/Ref($close,3)),Rank($volume),7) ) goes long (short) st…"
updated: "2026-04-11T20:47:28.605329"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Volatility-Adjusted Cross-Sectional Volume Reversal

## Summary

Hypothesis: Rank( -Sign(Delta($close,1))  Power(Std($close,5),0.5)  Corr(Rank($close/Ref($close,3)),Rank($volume),7) ) goes long (short) st…

## Hypothesis

Hypothesis: Rank( -Sign(Delta($close,1))  Power(Std($close,5),0.5)  Corr(Rank($close/Ref($close,3)),Rank($volume),7) ) goes long (short) st…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mult(Mult(Neg(Sign(Delta($close,1))),Sqrt(Std($close,5))),Corr(Div($close,Ref($close,3)),CSRank($volume),7)))```

**Math Formula**: R_i = \text{Rank}_t\left(-\text{sign}\left(\Delta P_{i,t}\right) \cdot \sqrt{\sigma_{i,t}^{(5)}} \cdot \rho_{i,t}^{(7)}\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
