---
title: "Cross-Sectional Term-Structure Slope Reversal with Liquidity Filter"
slug: "cross_sectional_term_structure_slope_reversal_with_liquidity_filter_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-6)) * Sign(Delta(2yr_swap_rate,1) - Delta(10yr_swap_rate,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, Delta(2y…"
updated: "2026-04-14T12:33:41"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.002"
rank_ic: "-0.028"
iteration: "3"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sectional Term-Structure Slope Reversal with Liquidity Filter

## Summary

Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-6)) * Sign(Delta(2yr_swap_rate,1) - Delta(10yr_swap_rate,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, Delta(2y…

## Hypothesis

Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-6)) * Sign(Delta(2yr_swap_rate,1) - Delta(10yr_swap_rate,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, Delta(2y…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Mul(Rank(Div(Delta($close,5),Add(Delta($volume,5),1e-6))),Sign(Delta(Sub(Ref($close,2),Ref($close,10)),1))),Neg(Rank(Ts_Percentile(Corr(GroupNeutral(Rank($close)),Delta(Sub(Ref($close,2),Ref($close,10)),21),21),60))),Rank(Inv(Add(Std($close,20),1))))```

**Math Formula**: R\left(\frac{\Delta_{5}P_{c}}{\Delta_{5}V+10^{-6}}\cdot\text{sgn}\left(\Delta_{1}r_{2y}-\Delta_{1}r_{10y}\right)\right)\cdot(-1)\cdot R\left(Q_{0.6}\left(\text{Corr}_{21}\left(R_{\text{ind}},\Delta_{21}(r_{2y}-r_{10y})\right)\right)\right)\cdot R\left(\frac{1}{1+\sigma_{20}}\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0020 / -0.0280
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
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
