---
title: "Intraday Volume-Weighted Return Dispersion"
slug: "intraday_volume_weighted_return_dispersion_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (Ts_Mean($close - $vwap, 3) / (Std($close - $vwap, 3) + 1e-6)) * Sign(Delta($volume,1)) ) ranks stocks by how far and consistently their closing prints d…"
updated: "2026-04-14T12:25:25"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.008"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Intraday Volume-Weighted Return Dispersion

## Summary

Rank( (Ts_Mean($close - $vwap, 3) / (Std($close - $vwap, 3) + 1e-6)) * Sign(Delta($volume,1)) ) ranks stocks by how far and consistently their closing prints d…

## Hypothesis

Rank( (Ts_Mean($close - $vwap, 3) / (Std($close - $vwap, 3) + 1e-6)) * Sign(Delta($volume,1)) ) ranks stocks by how far and consistently their closing prints d…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Div(Mean(Sub($close, $vwap), 3), Add(Std(Mean(Sub($close, $vwap), 3), 3), 0.000001)), Sign(Delta($volume, 1))))```

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\frac{\frac{1}{3}\sum_{k=0}^{2}(C_{i,t-k}-VWAP_{i,t-k})}{\sqrt{\frac{1}{3}\sum_{k=0}^{2}(C_{i,t-k}-VWAP_{i,t-k}-\mu_i)^2}+10^{-6}}\cdot\text{Sign}(V_{i,t}-V_{i,t-1})\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0080 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[momentum_family]]
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
