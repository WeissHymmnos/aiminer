---
title: "High-Frequency Volume-Volatility Reversal with Liquidity Shock Filter"
slug: "high_frequency_volume_volatility_reversal_with_liquidity_shock_filter_iter3"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Rank( (Delta($close,1) / (Std($close,5) + 1e-6))  Sign(Corr(Rank($volume), Rank(Std($close,3)), 10))  If(Rank($volume/Ref($volu…"
updated: "2026-04-11T20:50:34.778579"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# High-Frequency Volume-Volatility Reversal with Liquidity Shock Filter

## Summary

Hypothesis: Rank( (Delta($close,1) / (Std($close,5) + 1e-6))  Sign(Corr(Rank($volume), Rank(Std($close,3)), 10))  If(Rank($volume/Ref($volu…

## Hypothesis

Hypothesis: Rank( (Delta($close,1) / (Std($close,5) + 1e-6))  Sign(Corr(Rank($volume), Rank(Std($close,3)), 10))  If(Rank($volume/Ref($volu…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,1)/(Std($close,5)+0.000001)*Sign(Corr(Rank($volume),Rank(Std($close,3)),10))*If(Greater(Rank($volume/Ref($volume,1)),0.85),-1,1))```

**Math Formula**: \text{Signal}_i = \text{Rank}_U\left(\frac{\Delta(P_i,1)}{\sigma(P_i,5)+10^{-6}}\cdot\text{Sign}\left(\text{Corr}_{10}\left(\text{Rank}_U(V),\text{Rank}_U(\sigma(P,3))\right)\right)\cdot\left(\mathbb{1}_{\text{Rank}_U(V_i/V_i^{(-1)})>0.85}\cdot(-1)+\mathbb{1}_{\text{Rank}_U(V_i/V_i^{(-1)})\le 0.85}\cdot 1\right)\right)

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
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
