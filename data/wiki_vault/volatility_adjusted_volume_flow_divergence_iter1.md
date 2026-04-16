---
title: "Volatility-Adjusted Volume Flow Divergence"
slug: "volatility_adjusted_volume_flow_divergence_iter1"
type: "experiment_card"
status: "active"
summary: "Rank( Ts_Zscore( Delta($volume,1) / (Std($close,5) + 1e-6), 20 ) * Sign( Corr($close, $volume, 5) - Ref(Corr($close, $volume, 20),5) ) )"
updated: "2026-04-14T12:32:49"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.034"
rank_ic: "0.099"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Volatility-Adjusted Volume Flow Divergence

## Summary

Rank( Ts_Zscore( Delta($volume,1) / (Std($close,5) + 1e-6), 20 ) * Sign( Corr($close, $volume, 5) - Ref(Corr($close, $volume, 20),5) ) )

## Hypothesis

Rank( Ts_Zscore( Delta($volume,1) / (Std($close,5) + 1e-6), 20 ) * Sign( Corr($close, $volume, 5) - Ref(Corr($close, $volume, 20),5) ) )

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Div(Sub(Div(Delta($volume,1),Add(Std($close,5),0.000001)),Mean(Div(Delta($volume,1),Add(Std($close,5),0.000001)),20)),Std(Div(Delta($volume,1),Add(Std($close,5),0.000001)),20)),Sign(Sub(Corr($close,$volume,5),Corr(Ref($close,5),Ref($volume,5),20)))))```

**Math Formula**: \text{Rank}_{t}\left(\frac{\frac{V_{t}-V_{t-1}}{\sigma_{C,5,t}+10^{-6}}-\mu_{Z,20}}{\sigma_{Z,20}}\cdot\text{sign}\left(\rho_{CV,5,t}-\rho_{CV,20,t-5}\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0340 / 0.0990
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
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
