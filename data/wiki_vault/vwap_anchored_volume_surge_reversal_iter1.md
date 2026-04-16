---
title: "VWAP-Anchored Volume-Surge Reversal"
slug: "vwap_anchored_volume_surge_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that close well above their volume-weighted average price (VWAP) on a day when volume spikes to a 20-day high but intraday range shrinks tend to mean-re…"
updated: "2026-04-13T20:11:25"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.006"
rank_ic: "0.01"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# VWAP-Anchored Volume-Surge Reversal

## Summary

Stocks that close well above their volume-weighted average price (VWAP) on a day when volume spikes to a 20-day high but intraday range shrinks tend to mean-re…

## Hypothesis

Stocks that close well above their volume-weighted average price (VWAP) on a day when volume spikes to a 20-day high but intraday range shrinks tend to mean-re…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```CSRank(Delta($close,0)/$vwap)*CSRank($volume/Ts_Percentile($volume,20,100))*(-CSRank(Delta($high-$low,0)/Ref($high-$low,1)))```

**Math Formula**: Factor_{i,t}=\text{Rank}_t\left(\frac{\text{Close}_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right)\cdot\text{Rank}_t\left(\frac{\text{Volume}_{i,t}}{\max_{k=1..20}\text{Volume}_{i,t-k}}\right)\cdot\left(-\text{Rank}_t\left(\frac{\text{High}_{i,t}-\text{Low}_{i,t}}{\text{High}_{i,t-1}-\text{Low}_{i,t-1}}\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0060 / 0.0100
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[turnover_explosion_risk]]

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
