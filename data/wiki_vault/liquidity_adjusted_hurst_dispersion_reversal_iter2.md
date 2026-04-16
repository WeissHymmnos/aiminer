---
title: "Liquidity-Adjusted Hurst Dispersion Reversal"
slug: "liquidity_adjusted_hurst_dispersion_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,20)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (Std($close,5)/Mean($close,20)) * (1-Abs(Corr(Delta($close,1),Delta(…"
updated: "2026-04-14T12:33:09"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.001"
rank_ic: "0.136"
iteration: "2"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Hurst Dispersion Reversal

## Summary

Rank( (1-Hurst($close,20)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (Std($close,5)/Mean($close,20)) * (1-Abs(Corr(Delta($close,1),Delta(…

## Hypothesis

Rank( (1-Hurst($close,20)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (Std($close,5)/Mean($close,20)) * (1-Abs(Corr(Delta($close,1),Delta(…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 20)), Sign(Delta(Log($close), 1))), Div(Delta($volume, 1), Mean($volume, 20))), Div(Std($close, 5), Mean($close, 20))), Sub(1, Abs(Corr(Delta(Log($close), 1), Delta(Log($volume), 1), 15)))))```

**Math Formula**: R_{i,t}=\text{rank}_t\left(\left(1-H_{i,t}^{(20)}\right)\cdot\text{sign}\left(r_{i,t}^{(1)}\right)\cdot\frac{\Delta V_{i,t}^{(1)}}{\bar{V}_{i,t}^{(20)}}\cdot\frac{\sigma_{i,t}^{(5)}}{\bar{P}_{i,t}^{(20)}}\cdot\left(1-\left|\rho_{i,t}^{(15)}\right|\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0010 / 0.1360
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
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
