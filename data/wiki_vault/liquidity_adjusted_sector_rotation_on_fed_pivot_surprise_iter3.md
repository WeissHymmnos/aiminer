---
title: "Liquidity-Adjusted Sector Rotation on Fed-Pivot Surprise"
slug: "liquidity_adjusted_sector_rotation_on_fed_pivot_surprise_iter3"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  If(Corr(Delta($close,1), $fedfut3m, 15) > 0.02, 1, -1)  If(Rank($volume, 'sector')…"
updated: "2026-04-11T20:50:37.753293"
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

# Liquidity-Adjusted Sector Rotation on Fed-Pivot Surprise

## Summary

Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  If(Corr(Delta($close,1), $fedfut3m, 15) > 0.02, 1, -1)  If(Rank($volume, 'sector')…

## Hypothesis

Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  If(Corr(Delta($close,1), $fedfut3m, 15) > 0.02, 1, -1)  If(Rank($volume, 'sector')…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,5) / Delta($volume,5) * Sign(Corr(Delta($close,1), Ref($close,63),15) - 0.02) * Sign(0.4 - CSRank($volume)))```

**Math Formula**: R_{i,t}=\operatorname{Rank}_i\left(\frac{\Delta_5 P_{i,t}}{\Delta_5 V_{i,t}}\cdot\operatorname{sgn}\left(\operatorname{Corr}_{15}\left(\Delta_1 P_{i,t},F_{3m,t}\right)-0.02\right)\cdot\operatorname{sgn}\left(0.4-\operatorname{Rank}_{\text{sector},i}(V_{i,t})\right)\right)

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
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
