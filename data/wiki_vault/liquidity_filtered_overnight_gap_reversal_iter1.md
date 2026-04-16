---
title: "Liquidity-Filtered Overnight Gap Reversal"
slug: "liquidity_filtered_overnight_gap_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank over the last 5 days revert the next day; factor = sign(ΔCloseOve…"
updated: "2026-04-13T20:11:22"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "-0.033"
rank_ic: "-0.01"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Filtered Overnight Gap Reversal

## Summary

Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank over the last 5 days revert the next day; factor = sign(ΔCloseOve…

## Hypothesis

Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank over the last 5 days revert the next day; factor = sign(ΔCloseOve…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(Abs(Delta($close,1)),0.015),Sign(Delta($close,1))*Rank(Delta($volume,5)),0)```

**Math Formula**: r_{i,t+1}=\alpha+\beta\cdot\text{sign}(\Delta C_{i,t}^{\text{ON}})\cdot\text{Rank}_{i,t}(-\Delta DVOL_{i,t}^{5})\cdot\mathbb{I}(|\Delta C_{i,t}^{\text{ON}}|>0.015)+\varepsilon_{i,t+1}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0330 / -0.0100
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
