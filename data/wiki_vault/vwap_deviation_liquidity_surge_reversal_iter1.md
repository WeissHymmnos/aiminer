---
title: "VWAP-Deviation Liquidity Surge Reversal"
slug: "vwap_deviation_liquidity_surge_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that close far above their VWAP on sharply rising volume but with deteriorating order-flow imbalance (buy-initiated volume shrinking) tend to mean-rever…"
updated: "2026-04-13T20:11:28"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.098"
rank_ic: "0.017"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# VWAP-Deviation Liquidity Surge Reversal

## Summary

Stocks that close far above their VWAP on sharply rising volume but with deteriorating order-flow imbalance (buy-initiated volume shrinking) tend to mean-rever…

## Hypothesis

Stocks that close far above their VWAP on sharply rising volume but with deteriorating order-flow imbalance (buy-initiated volume shrinking) tend to mean-rever…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,0)/$vwap)*Rank(Delta($volume,1)/Ref($volume,1))*(-Rank(Delta((Delta($close,0)/Delta($high,0)-Delta($low,0)),3)/Ref((Delta($close,0)/Delta($high,0)-Delta($low,0)),3)))```

**Math Formula**: F_{i,t}=\text{Rank}_t\left(\frac{C_{i,t}-VWAP_{i,t}}{VWAP_{i,t}}\right)\cdot\text{Rank}_t\left(\frac{V_{i,t}}{V_{i,t-1}}-1\right)\cdot\left(-\text{Rank}_t\left(\frac{\frac{C_{i,t}-O_{i,t}}{H_{i,t}-L_{i,t}}}{\frac{C_{i,t-3}-O_{i,t-3}}{H_{i,t-3}-L_{i,t-3}}}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0980 / 0.0170
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
