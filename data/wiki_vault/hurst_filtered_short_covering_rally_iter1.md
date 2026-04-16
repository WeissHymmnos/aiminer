---
title: "Hurst-Filtered Short-Covering Rally"
slug: "hurst_filtered_short_covering_rally_iter1"
type: "experiment_card"
status: "failed"
summary: "Go long stocks whose 5-day price Hurst < 0.42 (mean-reverting) AND whose 2-day cumulative short-volume ratio (estimated via intraday tick-rule) jumps from bott…"
updated: "2026-04-14T12:04:08"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Filtered Short-Covering Rally

## Summary

Go long stocks whose 5-day price Hurst < 0.42 (mean-reverting) AND whose 2-day cumulative short-volume ratio (estimated via intraday tick-rule) jumps from bott…

## Hypothesis

Go long stocks whose 5-day price Hurst < 0.42 (mean-reverting) AND whose 2-day cumulative short-volume ratio (estimated via intraday tick-rule) jumps from bott…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less(Ts_Percentile($close,5,50),0.42),CSRank(Delta($volume,2)),0) * -CSRank(Delta($close,1))```

**Math Formula**: Factor = \mathbb{1}_{H_5<0.42}\cdot \text{Rank}\left(\Delta SVR_{2}\right)\cdot \left(-\text{Rank}\left(r_{1}\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
