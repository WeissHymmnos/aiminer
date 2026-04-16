---
title: "Hurst_Macro_Vol_Momentum"
slug: "hurst_macro_vol_momentum_iter1"
type: "experiment_card"
status: "active"
summary: "Hypothesis: In high-volatility, bear-trending markets, long-short portfolios formed on the interaction between 60-day Hurst exponent and th…"
updated: "2026-04-12T14:37:45.834203"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst_Macro_Vol_Momentum

## Summary

Hypothesis: In high-volatility, bear-trending markets, long-short portfolios formed on the interaction between 60-day Hurst exponent and th…

## Hypothesis

Hypothesis: In high-volatility, bear-trending markets, long-short portfolios formed on the interaction between 60-day Hurst exponent and th…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(Std($close,20),Ts_Percentile(Std($close,20),252,75)),Less(Mean($close,200),Ref(Mean($close,200),1))),If(And(Greater(CSRank($close),0.55),Less(Delta($close,20),0)),1,0)+If(And(Less(CSRank($close),0.45),Greater(Delta($close,20),0)),1,0),0)```

**Math Formula**: R_{i,t\rightarrow t+k}=\alpha+\beta_1 D^{H>0.55}_{i,t}\cdot D^{\Delta r<0}_t+\beta_2 D^{H<0.45}_{i,t}\cdot D^{\Delta r>0}_t+\gamma X_{i,t}+\epsilon_{i,t},\quad\text{with }k\in[21,63],\;\sigma^{mkt}_t>\theta_\sigma,\;\text{trend}_t<0

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
