---
title: "High-Frequency Volume-Price Divergence Reversal"
slug: "high_frequency_volume_price_divergence_reversal_iter1"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Rank( Delta($close,1) / (Delta($volume,1) + 1e-6)  Sign(Corr($vwap, $close, 3)) ) goes long (short) stocks whose 1-day price ch…"
updated: "2026-04-12T07:13:23.011936"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# High-Frequency Volume-Price Divergence Reversal

## Summary

Hypothesis: Rank( Delta($close,1) / (Delta($volume,1) + 1e-6)  Sign(Corr($vwap, $close, 3)) ) goes long (short) stocks whose 1-day price ch…

## Hypothesis

Hypothesis: Rank( Delta($close,1) / (Delta($volume,1) + 1e-6)  Sign(Corr($vwap, $close, 3)) ) goes long (short) stocks whose 1-day price ch…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mult(Delta($close,1)/(Delta($volume,1)+1e-6),Sign(Corr($vwap,$close,3))))```

**Math Formula**: R_{t} = \text{rank}_{i}\left(\frac{\Delta P_{i,t}}{\Delta V_{i,t}+10^{-6}}\cdot\text{sign}\left(\rho_{i,t}^{(3)}\left(\text{VWAP},P\right)\right)\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
