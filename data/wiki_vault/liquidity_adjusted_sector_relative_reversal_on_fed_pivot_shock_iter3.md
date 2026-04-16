---
title: "Liquidity-Adjusted Sector-Relative Reversal on Fed-Pivot Shock"
slug: "liquidity_adjusted_sector_relative_reversal_on_fed_pivot_shock_iter3"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta(Close,5) / Sqrt(Mean(Volume,5)))  If(Rank(Corr(Delta(Close,3),Delta(VIX,1),15))>0.7,-1,1)  Sign(Rank(Delta(Close,5…"
updated: "2026-04-11T20:47:32.478459"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Sector-Relative Reversal on Fed-Pivot Shock

## Summary

Hypothesis: Rank( (Delta(Close,5) / Sqrt(Mean(Volume,5)))  If(Rank(Corr(Delta(Close,3),Delta(VIX,1),15))>0.7,-1,1)  Sign(Rank(Delta(Close,5…

## Hypothesis

Hypothesis: Rank( (Delta(Close,5) / Sqrt(Mean(Volume,5)))  If(Rank(Corr(Delta(Close,3),Delta(VIX,1),15))>0.7,-1,1)  Sign(Rank(Delta(Close,5…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Divide(Delta($close,5),Sqrt(Mean($volume,5))),If(Greater(CSRank(Corr(Delta($close,3),Delta($vwap,1),15)),0.7),-1,1))) * Sign(Subtract(Rank(Delta($close,5)),CSRank(Delta($close,5))))```

**Math Formula**: \text{Rank}\left( \frac{\Delta(C_t,5)}{\sqrt{\text{Mean}(V_t,5)}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\text{Corr}\left(\Delta(C_t,3),\Delta(\text{VIX}_t,1),15\right)\right)\,>\,0.7\right\}}\cdot(-1) + \frac{\Delta(C_t,5)}{\sqrt{\text{Mean}(V_t,5)}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\text{Corr}\left(\Delta(C_t,3),\Delta(\text{VIX}_t,1),15\right)\right)\,\le\,0.7\right\}}\cdot1 \right) \cdot \text{Sign}\left(\text{Rank}\left(\Delta(C_t,5)\right) - \text{Rank}_{\text{sector}}\left(\Delta(C_t,5)\right)\right)

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
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
