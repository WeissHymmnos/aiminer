---
title: "Tail-Hedge Net Demand Reversal"
slug: "tail_hedge_net_demand_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Over the last 5 trading days, stocks whose cumulative put/call open-interest ratio jumps into the top decile while simultaneously exhibiting the largest single…"
updated: "2026-04-13T20:12:01"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.011"
rank_ic: "0.088"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Tail-Hedge Net Demand Reversal

## Summary

Over the last 5 trading days, stocks whose cumulative put/call open-interest ratio jumps into the top decile while simultaneously exhibiting the largest single…

## Hypothesis

Over the last 5 trading days, stocks whose cumulative put/call open-interest ratio jumps into the top decile while simultaneously exhibiting the largest single…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($volume,5),5) * (-Rank(Delta($close,1),1))```

**Math Formula**: R_{i,t+1:t+5} = \alpha + \beta \cdot \text{Factor}_{i,t} + \epsilon_{i,t}\quad\text{where}\quad \text{Factor}_{i,t} = \text{Rank}_t\left(\Delta\text{PutCallOI}_{i,t-5:t},5\right) \cdot \left(-\text{Rank}_t\left(\Delta\text{25dSkew}_{i,t-1:t},1\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0110 / 0.0880
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
