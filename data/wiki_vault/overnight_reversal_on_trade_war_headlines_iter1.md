---
title: "Overnight-Reversal-On-Trade-War-Headlines"
slug: "overnight_reversal_on_trade_war_headlines_iter1"
type: "experiment_card"
status: "failed"
summary: "After 21:00 UTC when headlines cross about renewed US-China trade-war tariffs, equities that drop >2 % in the overnight session revert the next cash day if the…"
updated: "2026-04-13T19:11:10"
tags: ["You are an expert in mean-reversion trad", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "threshold_timing_execution"]
ic: "-0.042"
rank_ic: "0.137"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# Overnight-Reversal-On-Trade-War-Headlines

## Summary

After 21:00 UTC when headlines cross about renewed US-China trade-war tariffs, equities that drop >2 % in the overnight session revert the next cash day if the…

## Hypothesis

After 21:00 UTC when headlines cross about renewed US-China trade-war tariffs, equities that drop >2 % in the overnight session revert the next cash day if the…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Less(Delta($open,1)/Ref($close,1),-0.02), Ref($volume,1)==1, Ref($volume,8)==0), 0.008, If(And(Less(Delta($open,1)/Ref($close,1),-0.02), Ref($volume,1)==1, Ref($volume,8)==0), -0.009, 0))```

**Math Formula**: R_{i,t+1}=\begin{cases}+0.8\% & \text{if } r_{i,t}^{\text{overnight}}<-2\%,\ H_t=1,\ P_{t+8}=0,\ \text{entry at open, exit at close}\\ -0.9\% & \text{if } r_{i,t}^{\text{overnight}}<-2\%,\ H_t=1,\ P_{t+8}=0,\ \text{stop-loss hit}\\ 0 & \text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0420 / 0.1370
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
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
