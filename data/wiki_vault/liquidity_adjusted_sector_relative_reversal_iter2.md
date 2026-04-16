---
title: "Liquidity-Adjusted Sector-Relative Reversal"
slug: "liquidity_adjusted_sector_relative_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,1)  (1/Rank($volume))  Sign(Rank($close/Ref($close,5)) - Rank($close/Ref($close,5),'sect…"
updated: "2026-04-11T20:47:14.257694"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Sector-Relative Reversal

## Summary

Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,1)  (1/Rank($volume))  Sign(Rank($close/Ref($close,5)) - Rank($close/Ref($close,5),'sect…

## Hypothesis

Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,1)  (1/Rank($volume))  Sign(Rank($close/Ref($close,5)) - Rank($close/Ref($close,5),'sect…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),-1),Ref($close,1)),Divide(1,Rank($volume))),Sign(Minus(Rank(Divide($close,Ref($close,5))),CSRank(Divide($close,Ref($close,5)))))))```

**Math Formula**: R = \text{Rank}\left(\frac{\text{Ref}(C,1)-O}{\text{Ref}(C,1)} \cdot \frac{1}{\text{Rank}(V)} \cdot \text{Sign}\left(\text{Rank}\left(\frac{C}{\text{Ref}(C,5)}\right) - \text{Rank}\left(\frac{C}{\text{Ref}(C,5)},\text{sector}\right)\right)\right)

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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
