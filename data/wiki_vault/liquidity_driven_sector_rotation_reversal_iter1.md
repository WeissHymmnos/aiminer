---
title: "Liquidity-Driven Sector Rotation Reversal"
slug: "liquidity_driven_sector_rotation_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  Sign(Rank($volume,63) - 0.5)  Sign(Rank($close/Ref($close,21)) - Rank($close/Ref($c…"
updated: "2026-04-11T20:50:07.902792"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Driven Sector Rotation Reversal

## Summary

Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  Sign(Rank($volume,63) - 0.5)  Sign(Rank($close/Ref($close,21)) - Rank($close/Ref($c…

## Hypothesis

Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  Sign(Rank($volume,63) - 0.5)  Sign(Rank($close/Ref($close,21)) - Rank($close/Ref($c…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Delta($close,5),Delta($volume,5)),Sign(Subtract(Rank(Mean($volume,63)),0.5))),Sign(Subtract(Rank(Divide($close,Ref($close,21))),CSRank(Divide($close,Ref($close,21)))))))```

**Math Formula**: R = \text{Rank}\left( \frac{\Delta(C,5)}{\Delta(V,5)} \cdot \text{Sign}\left(\text{Rank}(V,63) - 0.5\right) \cdot \text{Sign}\left(\text{Rank}\left(\frac{C}{C_{21}}\right) - \text{Rank}_{\text{sector}}\left(\frac{C}{C_{21}}\right)\right) \right)

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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
