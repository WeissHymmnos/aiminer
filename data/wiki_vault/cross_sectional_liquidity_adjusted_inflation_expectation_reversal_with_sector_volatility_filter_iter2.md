---
title: "Cross-Sectional Liquidity-Adjusted Inflation-Expectation Reversal with Sector-Volatility Filter"
slug: "cross_sectional_liquidity_adjusted_inflation_expectation_reversal_with_sector_volatility_filter_iter2"
type: "experiment_card"
status: "active"
summary: "Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(5y5y_inflation_forward,1)) ) * (-1) * Rank(Quantile(Corr(SectorReturn, 5y5y_inflation_forward, 21)…"
updated: "2026-04-14T12:33:16"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "implementation_drift_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.039"
rank_ic: "0.132"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Cross-Sectional Liquidity-Adjusted Inflation-Expectation Reversal with Sector-Volatility Filter

## Summary

Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(5y5y_inflation_forward,1)) ) * (-1) * Rank(Quantile(Corr(SectorReturn, 5y5y_inflation_forward, 21)…

## Hypothesis

Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(5y5y_inflation_forward,1)) ) * (-1) * Rank(Quantile(Corr(SectorReturn, 5y5y_inflation_forward, 21)…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Mul(Rank(Mul(Div(Delta($close,3),Add(Delta($volume,3),0.000001)),Sign(Delta($vwap,1))),-1),Mul(Rank(Percentile(Corr(Ref($close,1),$vwap,21))),Rank(Inv(Add(Std(Ref($close,1),10),0.000001)))))```

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\frac{\Delta_3 P_{i,t}}{\Delta_3 V_{i,t}+10^{-6}}\cdot\text{Sign}\left(\Delta_1 F_{t}\right)\right)\cdot(-1)\cdot\text{Rank}_i\left(\text{Quantile}_{0.8}\left(\text{Corr}_{21}\left(R_{\text{sec},t},F_{t}\right)\right)\right)\cdot\text{Rank}_i\left(\frac{1}{\sigma_{\text{sec},10d}+10^{-6}}\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0390 / 0.1320
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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
