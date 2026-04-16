---
title: "Central-Bank-Dampened Flow Rebound"
slug: "central_bank_dampened_flow_rebound_iter2"
type: "experiment_card"
status: "active"
summary: "Long stocks whose 2-day cumulative order-flow imbalance (Sign(Close-Open)*Volume) is in the bottom decile (extreme selling) yet the latest 15-minute closing st…"
updated: "2026-04-13T20:12:07"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.068"
rank_ic: "0.04"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Central-Bank-Dampened Flow Rebound

## Summary

Long stocks whose 2-day cumulative order-flow imbalance (Sign(Close-Open)*Volume) is in the bottom decile (extreme selling) yet the latest 15-minute closing st…

## Hypothesis

Long stocks whose 2-day cumulative order-flow imbalance (Sign(Close-Open)*Volume) is in the bottom decile (extreme selling) yet the latest 15-minute closing st…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less(Rank(Sum(If(Greater($close - $open, 0), 1, If(Less($close - $open, 0), -1, 0)) * $volume, 2)), 0.1), Rank(Divide(Divide($close - $low, $high - $low) - Ts_Percentile(Divide(Ref($close, 0) - Ref($low, 0), Ref($high, 0) - Ref($low, 0)), 3, 100), Std(Divide(Ref($close, 0) - Ref($low, 0), Ref($high, 0) - Ref($low, 0)), 3))), 0)```

**Math Formula**: \text{Factor}_t = \begin{cases}\text{Rank}\left(\frac{\frac{C_t - L_t}{H_t - L_t} - \max_{k=0,1,2}\left(\frac{C_{t-k} - L_{t-k}}{H_{t-k} - L_{t-k}}\right)}{\text{Std}_{k=0,1,2}\left(\frac{C_{t-k} - L_{t-k}}{H_{t-k} - L_{t-k}}\right)}\right) & \text{if } \text{Rank}\left(\text{Sign}(C_t - O_t)V_t + \text{Sign}(C_{t-1} - O_{t-1})V_{t-1}\right) < 0.1 \\ 0 & \text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0680 / 0.0400
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

## Next Steps

Promote or refine after collecting stronger evidence.
