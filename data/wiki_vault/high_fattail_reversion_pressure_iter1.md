---
title: "High-FatTail-Reversion-Pressure"
slug: "high_fattail_reversion_pressure_iter1"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Daily stocks whose (Close−Low)/(High−Low) is in the top 20 % of the cross-section but whose volume spike (ΔVolume,1) is simulta…"
updated: "2026-04-13T13:52:08.348257"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# High-FatTail-Reversion-Pressure

## Summary

Hypothesis: Daily stocks whose (Close−Low)/(High−Low) is in the top 20 % of the cross-section but whose volume spike (ΔVolume,1) is simulta…

## Hypothesis

Hypothesis: Daily stocks whose (Close−Low)/(High−Low) is in the top 20 % of the cross-section but whose volume spike (ΔVolume,1) is simulta…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(Rank(Div(Sub($close,$low),Sub($high,$low))),0.8),Less(Rank(Delta($volume,1)),0.2)),-1,0)```

**Math Formula**: \left\{i:t\;\Big|\;\text{Rank}_{CS,t}\left(\frac{\text{Close}_{i,t}-\text{Low}_{i,t}}{\text{High}_{i,t}-\text{Low}_{i,t}}\right)\geq 0.8\;\land\;\text{Rank}_{CS,t}\left(\Delta\text{Volume}_{i,t,1}\right)\leq 0.2\right\}\;\Rightarrow\;\mathbb{E}\left[R_{i,t+1}-R_{f,t+1}\right]<0

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
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
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
