---
title: "VWAP Liquidity Gradient Reversal"
slug: "vwap_liquidity_gradient_reversal_iter3"
type: "experiment_card"
status: "active"
summary: "Rank( Delta($close,1) / (Ts_Mean($volume,3) + 1e-6) * (1 - Abs(Rank(($close - $vwap)/$vwap))) )"
updated: "2026-04-14T12:26:09"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "implementation_drift_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "-0.047"
rank_ic: "0.045"
iteration: "3"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# VWAP Liquidity Gradient Reversal

## Summary

Rank( Delta($close,1) / (Ts_Mean($volume,3) + 1e-6) * (1 - Abs(Rank(($close - $vwap)/$vwap))) )

## Hypothesis

Rank( Delta($close,1) / (Ts_Mean($volume,3) + 1e-6) * (1 - Abs(Rank(($close - $vwap)/$vwap))) )

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Div(Delta($close, 1), Add(Mean($volume, 3), 1e-6)))```

**Math Formula**: R_{i,t}=\text{rank}_i\left(\frac{\Delta P_{i,t}}{\bar{V}_{i,t-1:t-3}+10^{-6}}\cdot\left(1-\left|\text{rank}_i\left(\frac{P_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right)\right|\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** -0.0470 / 0.0450
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[implementation_drift_risk]]

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
