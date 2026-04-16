---
title: "Liquidity Shock Reversal"
slug: "liquidity_shock_reversal_iter1"
type: "experiment_card"
status: "active"
summary: "Within the first 30 minutes after a sudden ≥1.5% index gap down on no major headline, fade the 3-minute RSI <25 extreme by buying the most short-term oversold…"
updated: "2026-04-13T19:11:09"
tags: ["You are an expert in mean-reversion trad", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.118"
rank_ic: "-0.035"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity Shock Reversal

## Summary

Within the first 30 minutes after a sudden ≥1.5% index gap down on no major headline, fade the 3-minute RSI <25 extreme by buying the most short-term oversold…

## Hypothesis

Within the first 30 minutes after a sudden ≥1.5% index gap down on no major headline, fade the 3-minute RSI <25 extreme by buying the most short-term oversold…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(LessEqual(0, 0), LessEqual(0, 0), LessEqual(Delta($close, 1) / Ref($close, 1), -0.015), LessEqual(0, 0), Less(Ts_Rank(Mean($close, 3), 3), 25), LessEqual(CSRank($close), 50)), 1, 0)```

**Math Formula**: \text{Entry}_t = \left\{ \begin{array}{ll} 1, & \text{if } t \in [T_0, T_0+30\text{min}] \,\land\, \frac{I_{t_0}-I_{t_0-1}}{I_{t_0-1}} \leq -0.015 \,\land\, \text{Headline}_{t_0}=0 \,\land\, \text{RSI}_{3\text{min}}(t) < 25 \,\land\, \text{CapRank}_i(t) \leq K \\ 0, & \text{otherwise} \end{array} \right. \quad\quad \text{Exit}_t = \min\!\left\{ \inf\!\left\{ t' > t \mid \text{RSI}_{3\text{min}}(t') > 55 \right\},\; 15\!:\!45 \right\)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.1180 / -0.0350
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
