---
title: "Cross-Sectional Hurst-Term Structure Volatility Reversal"
slug: "cross_sectional_hurst_term_structure_volatility_reversal_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( (1 - Hurst($close,18)) * Sign(Delta($close,1)) * (Delta($vwap,1)/$close) * (Std($close,5)/Std($close,30)) ) goes long (short) stocks whose 1-day return i…"
updated: "2026-04-14T12:33:31"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.006"
rank_ic: "-0.013"
iteration: "3"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sectional Hurst-Term Structure Volatility Reversal

## Summary

Rank( (1 - Hurst($close,18)) * Sign(Delta($close,1)) * (Delta($vwap,1)/$close) * (Std($close,5)/Std($close,30)) ) goes long (short) stocks whose 1-day return i…

## Hypothesis

Rank( (1 - Hurst($close,18)) * Sign(Delta($close,1)) * (Delta($vwap,1)/$close) * (Std($close,5)/Std($close,30)) ) goes long (short) stocks whose 1-day return i…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Sub(1, Ts_Rank($close, 18)), Mul(Sign(Delta($close, 1)), Mul(Div(Delta($vwap, 1), $close), Div(Std($close, 5), Std($close, 30))))))```

**Math Formula**: R_i = \text{rank}_i\left(\left(1 - H_i\right)\cdot\text{sign}\left(r_i\right)\cdot\frac{\Delta v_i}{c_i}\cdot\frac{\sigma_{i,5}}{\sigma_{i,30}}\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0060 / -0.0130
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
