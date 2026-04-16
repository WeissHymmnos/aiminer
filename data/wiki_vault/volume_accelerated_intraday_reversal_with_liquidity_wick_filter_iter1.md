---
title: "Volume-Accelerated Intraday Reversal with Liquidity Wick Filter"
slug: "volume_accelerated_intraday_reversal_with_liquidity_wick_filter_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($close,1) / (Power($high-$low,0.5)+1e-6))  If(Rank($volume/Ref($volume,1))>0.8, -1, 1)  Sign(Mean($close,3)-$close…"
updated: "2026-04-11T20:46:57.758445"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Volume-Accelerated Intraday Reversal with Liquidity Wick Filter

## Summary

Hypothesis: Rank( (Delta($close,1) / (Power($high-$low,0.5)+1e-6))  If(Rank($volume/Ref($volume,1))>0.8, -1, 1)  Sign(Mean($close,3)-$close…

## Hypothesis

Hypothesis: Rank( (Delta($close,1) / (Power($high-$low,0.5)+1e-6))  If(Rank($volume/Ref($volume,1))>0.8, -1, 1)  Sign(Mean($close,3)-$close…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Add(Multiply(Divide(Delta($close,1),Add(Sqrt(Subtract($high,$low)),0.000001)),If(Greater(Rank(Divide($volume,Ref($volume,1))),0.8),-1,1)),Multiply(Divide(Delta($close,1),Add(Sqrt(Subtract($high,$low)),0.000001)),If(LessEqual(Rank(Divide($volume,Ref($volume,1))),0.8),1,1))),Sign(Subtract(Mean($close,3),$close))))```

**Math Formula**: \text{Rank}\left( \frac{\Delta C_t}{\sqrt{H_t-L_t}+10^{-6}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\frac{V_t}{V_{t-1}}\right)>0.8\right\}}\cdot(-1) + \frac{\Delta C_t}{\sqrt{H_t-L_t}+10^{-6}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\frac{V_t}{V_{t-1}}\right)\le 0.8\right\}}\cdot(+1) \right) \cdot \text{sgn}\left(\frac{C_t+C_{t-1}+C_{t-2}}{3}-C_t\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
