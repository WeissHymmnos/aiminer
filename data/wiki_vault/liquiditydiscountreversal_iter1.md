---
title: "LiquidityDiscountReversal"
slug: "liquiditydiscountreversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,2)  If(Rank($volume/Ref($volume,1))<0.25,-1,1)  If(Rank($close/Ref($close,1))<0.3,1,-1)…"
updated: "2026-04-11T20:46:59.585901"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# LiquidityDiscountReversal

## Summary

Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,2)  If(Rank($volume/Ref($volume,1))<0.25,-1,1)  If(Rank($close/Ref($close,1))<0.3,1,-1)…

## Hypothesis

Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,2)  If(Rank($volume/Ref($volume,1))<0.25,-1,1)  If(Rank($close/Ref($close,1))<0.3,1,-1)…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),$open),Ref($close,2)),Sign(Sub(0.25,Rank(Divide($volume,Ref($volume,1)))))),Sign(Sub(Rank(Divide($close,Ref($close,1))),0.3))))```

**Math Formula**: R_{i,t}=\text{Rank}_t\left(\frac{\text{Ref}(C_{i,t},1)-O_{i,t}}{\text{Ref}(C_{i,t},2)}\cdot\text{sgn}\left(0.25-\text{Rank}_t\left(\frac{V_{i,t}}{\text{Ref}(V_{i,t},1)}\right)\right)\cdot\text{sgn}\left(\text{Rank}_t\left(\frac{C_{i,t}}{\text{Ref}(C_{i,t},1)}\right)-0.3\right)\right)

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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
