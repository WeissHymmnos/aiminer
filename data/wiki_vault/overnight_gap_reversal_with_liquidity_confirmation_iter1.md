---
title: "Overnight Gap Reversal with Liquidity Confirmation"
slug: "overnight_gap_reversal_with_liquidity_confirmation_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank versus their 5-day average reverse next-day; factor = -Rank(GapUp…"
updated: "2026-04-13T20:11:23"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.005"
rank_ic: "-0.013"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Overnight Gap Reversal with Liquidity Confirmation

## Summary

Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank versus their 5-day average reverse next-day; factor = -Rank(GapUp…

## Hypothesis

Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank versus their 5-day average reverse next-day; factor = -Rank(GapUp…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```-1 * Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank(Delta($close * $volume,5)) * Greater(($open - Ref($close,1)) / Ref($close,1), 0.015) * Less(($high - $low) / $open, 0.02)```

**Math Formula**: F_{i,t}= -\text{Rank}_t\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\text{Rank}_t\left(\Delta\left(C_{i,t}\cdot V_{i,t},5\right)\right)\cdot\mathbf{1}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}>0.015\right)\cdot\mathbf{1}\left(\frac{H_{i,t}-L_{i,t}}{O_{i,t}}<0.02\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0050 / -0.0130
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
