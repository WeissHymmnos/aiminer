---
title: "Cross-Sectional Gamma-Squeeze Reversal with Gamma-Adjusted Volume"
slug: "cross_sectional_gamma_squeeze_reversal_with_gamma_adjusted_volume_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank stocks by how much their 1-day return is stretched relative to the contemporaneous change in 0DTE option gamma, scaled by the deviation of volume from its…"
updated: "2026-04-14T12:26:00"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.006"
rank_ic: "-0.02"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sectional Gamma-Squeeze Reversal with Gamma-Adjusted Volume

## Summary

Rank stocks by how much their 1-day return is stretched relative to the contemporaneous change in 0DTE option gamma, scaled by the deviation of volume from its…

## Hypothesis

Rank stocks by how much their 1-day return is stretched relative to the contemporaneous change in 0DTE option gamma, scaled by the deviation of volume from its…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```CSRank(Neg(Sub(Log(Div($close,Ref($close,1))),Add(GroupNeutral(Log(Div($close,Ref($close,1)))),Mul(GroupNeutral(Delta($volume,1)),Div(Corr(Log(Div($close,Ref($close,1))),Delta($volume,1),20),Std(Delta($volume,1),20))))))))```

**Math Formula**: R_{i,t}=\frac{r_{i,t}}{\Delta\Gamma_{i,t}\,/\,(V_{i,t}-\min_{k=1..10}V_{i,t-k})}\quad\text{with}\quad\text{signal}=\text{rank}(-\hat{\varepsilon}_{i,t})\;\text{for long},\;\text{rank}(+\hat{\varepsilon}_{i,t})\;\text{for short},\;\text{where}\;r_{i,t}=\ln(P_{i,t}/P_{i,t-1}),\;\Delta\Gamma_{i,t}=\Gamma_{i,t}^{0DTE}-\Gamma_{i,t-1}^{0DTE},\;\hat{\varepsilon}_{i,t}=r_{i,t}-\hat{\alpha}-\hat{\beta}\Delta\Gamma_{i,t}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0060 / -0.0200
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
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
