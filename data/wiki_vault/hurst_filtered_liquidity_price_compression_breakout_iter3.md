---
title: "Hurst-Filtered Liquidity-Price Compression Breakout"
slug: "hurst_filtered_liquidity_price_compression_breakout_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Delta($close,1)) * (Mean($high-$low,3)/Mean($high-$low,20)-1) * (Mean($volume,3)/Mean($volume,20)-1) ) goes…"
updated: "2026-04-14T12:09:21"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0044"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Liquidity-Price Compression Breakout

## Summary

Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Delta($close,1)) * (Mean($high-$low,3)/Mean($high-$low,20)-1) * (Mean($volume,3)/Mean($volume,20)-1) ) goes…

## Hypothesis

Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Delta($close,1)) * (Mean($high-$low,3)/Mean($high-$low,20)-1) * (Mean($volume,3)/Mean($volume,20)-1) ) goes…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(Greater(Mean($high-$low,21),0.45),Less(Mean($high-$low,21),0.7)),Sign(Delta($close,1))*(Mean($high-$low,3)/Mean($high-$low,20)-1)*(Mean($volume,3)/Mean($volume,20)-1),0))```

**Math Formula**: R = \text{rank}\left[ \mathbb{1}_{[0.45,0.7]}\left(H_{21}\right) \cdot \text{sgn}\left(\Delta C_{1}\right) \cdot \left(\frac{\bar{R}_{3}}{\bar{R}_{20}}-1\right) \cdot \left(\frac{\bar{V}_{3}}{\bar{V}_{20}}-1\right) \right]

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0044 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
