---
title: "Liquidity-Triggered Overnight Gap Reversal"
slug: "liquidity_triggered_overnight_gap_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that open with a positive gap >0.5% but show a sudden 1-day surge in cancelled order volume (proxy for cancelled buy-orders) reverse intraday; factor =…"
updated: "2026-04-13T20:11:20"
tags: ["利用复杂网络与知识图谱挖掘产业链关联的图计算专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "implementation_drift_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.007"
rank_ic: "0.066"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Triggered Overnight Gap Reversal

## Summary

Stocks that open with a positive gap >0.5% but show a sudden 1-day surge in cancelled order volume (proxy for cancelled buy-orders) reverse intraday; factor =…

## Hypothesis

Stocks that open with a positive gap >0.5% but show a sudden 1-day surge in cancelled order volume (proxy for cancelled buy-orders) reverse intraday; factor =…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(Delta($open, $close), 0.005), -Rank(Delta($open, $close)) * Rank(Delta($volume, 1)), 0)```

**Math Formula**: f_t = \begin{cases}-\mathrm{rank}(\mathrm{OpenGap}_t)\cdot\mathrm{rank}(\Delta\mathrm{CancelVolume}_t) & \text{if }\mathrm{OpenGap}_t>0.005\\ 0 & \text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0070 / 0.0660
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[implementation_drift_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
