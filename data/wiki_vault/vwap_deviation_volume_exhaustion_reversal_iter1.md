---
title: "VWAP-Deviation Volume Exhaustion Reversal"
slug: "vwap_deviation_volume_exhaustion_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that close well above their volume-weighted average price (VWAP) on sharply shrinking volume over the past two sessions tend to mean-revert the next day…"
updated: "2026-04-13T20:11:28"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0121"
rank_ic: "-0.0148"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# VWAP-Deviation Volume Exhaustion Reversal

## Summary

Stocks that close well above their volume-weighted average price (VWAP) on sharply shrinking volume over the past two sessions tend to mean-revert the next day…

## Hypothesis

Stocks that close well above their volume-weighted average price (VWAP) on sharply shrinking volume over the past two sessions tend to mean-revert the next day…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```CSRank(($close - $vwap) / $vwap) * CSRank(-Delta($volume, 2)) * -1```

**Math Formula**: E\left[\frac{r_{i,t+1}}{\sigma_{i,t+1}}\right]=-\alpha\cdot\text{Rank}_{c}\left(\frac{C_{i,t}-VWAP_{i,t}}{VWAP_{i,t}}\right)\cdot\text{Rank}_{c}\left(-\Delta_{2}V_{i,t}\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0121 / -0.0148
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
