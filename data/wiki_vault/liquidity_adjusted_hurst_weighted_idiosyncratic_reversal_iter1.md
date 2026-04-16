---
title: "Liquidity-Adjusted Hurst-Weighted Idiosyncratic Reversal"
slug: "liquidity_adjusted_hurst_weighted_idiosyncratic_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,15))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Ref(Mean($volume,30),1)) * (1-Abs(Corr(Delta($close,1),Delta($vwap,1),5))) ) goes long…"
updated: "2026-04-14T12:32:46"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.133"
rank_ic: "-0.006"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Adjusted Hurst-Weighted Idiosyncratic Reversal

## Summary

Rank( (1-Hurst($close,15))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Ref(Mean($volume,30),1)) * (1-Abs(Corr(Delta($close,1),Delta($vwap,1),5))) ) goes long…

## Hypothesis

Rank( (1-Hurst($close,15))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Ref(Mean($volume,30),1)) * (1-Abs(Corr(Delta($close,1),Delta($vwap,1),5))) ) goes long…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Pow(Sub(1, Ts_Rank($close, 15)), 2) * Sign(Delta($close, 1)) * Div(Delta($volume, 1), Mean(Ref($volume, 1), 30)) * Sub(1, Abs(Corr(Delta($close, 1), Delta($vwap, 1), 5))))```

**Math Formula**: R = \text{rank}\left(\left(1 - H_{15}(C)\right)^2 \cdot \text{sign}\left(\Delta_1 C\right) \cdot \frac{\Delta_1 V}{\mu_{30}(V)} \cdot \left(1 - \left|\rho_{5}\left(\Delta_1 C, \Delta_1 \text{vwap}\right)\right|\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.1330 / -0.0060
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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
