---
title: "Liquidity-Adjusted Intraday Momentum Reversal"
slug: "liquidity_adjusted_intraday_momentum_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Stocks whose intraday closing strength (Close-Low)/(High-Low) is high but accompanied by declining liquidity rank over the last…"
updated: "2026-04-13T13:52:06.400729"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Intraday Momentum Reversal

## Summary

Hypothesis: Stocks whose intraday closing strength (Close-Low)/(High-Low) is high but accompanied by declining liquidity rank over the last…

## Hypothesis

Hypothesis: Stocks whose intraday closing strength (Close-Low)/(High-Low) is high but accompanied by declining liquidity rank over the last…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(($close - $low) / ($high - $low)) * (-Rank($volume - Ref($volume, 3)))```

**Math Formula**: \text{Factor}_{i,t}=\text{Rank}_{\text{cross}}
\left(\frac{C_{i,t}-L_{i,t}}{H_{i,t}-L_{i,t}}\right)
\times
\left(-\text{Rank}_{\text{cross}}\left(V_{i,t}-V_{i,t-3}\right)\right)

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
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
