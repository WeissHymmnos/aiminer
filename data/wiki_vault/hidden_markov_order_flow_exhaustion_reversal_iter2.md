---
title: "Hidden-Markov Order-Flow Exhaustion Reversal"
slug: "hidden_markov_order_flow_exhaustion_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Among stocks whose 3-day hidden-Markov regime probability of ‘High-Volume-Pressure’ drops below 30 % while their 1-day closing strength ((Close-Low)/(High-Low)…"
updated: "2026-04-13T20:11:55"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.106"
rank_ic: "-0.006"
iteration: "2"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hidden-Markov Order-Flow Exhaustion Reversal

## Summary

Among stocks whose 3-day hidden-Markov regime probability of ‘High-Volume-Pressure’ drops below 30 % while their 1-day closing strength ((Close-Low)/(High-Low)…

## Hypothesis

Among stocks whose 3-day hidden-Markov regime probability of ‘High-Volume-Pressure’ drops below 30 % while their 1-day closing strength ((Close-Low)/(High-Low)…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less($close, 0.3), Rank(($close - $low) / ($high - $low)) * (-Rank(Delta($close, 1))), 0)```

**Math Formula**: r_{i,t+1}=\alpha+\beta\cdot f_{i,t}+\epsilon_{i,t}\quad\text{with}\quad f_{i,t}=\begin{cases}\text{Rank}_{c}\left(\frac{C_{i,t}-L_{i,t}}{H_{i,t}-L_{i,t}}\right)\cdot\left(-\text{Rank}_{c}\left(\Delta P_{i,t}^{\text{HVP}}\right)\right)&\text{if }P_{i,t}^{\text{HVP}}<0.3\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.1060 / -0.0060
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
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
