---
title: "Liquidity-Adjusted Inflation-Beta Reversal with Policy-Uncertainty Filter"
slug: "liquidity_adjusted_inflation_beta_reversal_with_policy_uncertainty_filter_iter1"
type: "experiment_card"
status: "active"
summary: "Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(PPI_surprise,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, PPI_surprise, 21), 0.7)) * Rank(2-y…"
updated: "2026-04-14T12:32:49"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.031"
rank_ic: "0.07"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Inflation-Beta Reversal with Policy-Uncertainty Filter

## Summary

Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(PPI_surprise,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, PPI_surprise, 21), 0.7)) * Rank(2-y…

## Hypothesis

Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(PPI_surprise,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, PPI_surprise, 21), 0.7)) * Rank(2-y…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Neg(Mul(Rank(Div(Delta($close,3),Add(Delta($volume,3),0.000001))),Rank(Ts_Percentile(Corr($close,$volume,21),21,70))))```

**Math Formula**: -1 \cdot \text{Rank}\left(\frac{\Delta_3 \text{Close}}{\Delta_3 \text{Volume}+10^{-6}} \cdot \text{Sign}(\Delta_1 \text{PPI_surprise})\right) \cdot \text{Rank}\left(\text{Quantile}_{0.7}\left(\text{Corr}_{21}(\text{IndustryReturn},\text{PPI_surprise})\right)\right) \cdot \text{Rank}\left(\frac{\text{2-yr_swap_volatility}}{\text{market_cap}}\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0310 / 0.0700
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
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
