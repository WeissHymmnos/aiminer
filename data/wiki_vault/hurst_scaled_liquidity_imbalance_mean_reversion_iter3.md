---
title: "Hurst-Scaled Liquidity-Imbalance Mean-Reversion"
slug: "hurst_scaled_liquidity_imbalance_mean_reversion_iter3"
type: "experiment_card"
status: "active"
summary: "Rank( (1-Hurst($close,24)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Delta($close,1),Delta($volume,1),10)) ) goes long (short) st…"
updated: "2026-04-14T12:26:17"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.05"
rank_ic: "0.148"
iteration: "3"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Scaled Liquidity-Imbalance Mean-Reversion

## Summary

Rank( (1-Hurst($close,24)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Delta($close,1),Delta($volume,1),10)) ) goes long (short) st…

## Hypothesis

Rank( (1-Hurst($close,24)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Delta($close,1),Delta($volume,1),10)) ) goes long (short) st…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 24)), Sign(Delta($close, 1))), Div(Delta($volume, 1), Mean($volume, 20))), Sub(1, Corr(Delta($close, 1), Delta($volume, 1), 10))))```

**Math Formula**: R = \text{rank}\left(\left(1 - H_{24}\right) \cdot \text{sign}\left(\Delta P_{1}\right) \cdot \frac{\Delta V_{1}}{\bar{V}_{20}} \cdot \left(1 - \rho_{10}\left(\Delta P_{1}, \Delta V_{1}\right)\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0500 / 0.1480
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
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
