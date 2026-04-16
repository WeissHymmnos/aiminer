---
title: "OrderFlow Imbalance Micro-Trend Exhaustion"
slug: "orderflow_imbalance_micro_trend_exhaustion_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks whose bid/ask order-flow imbalance (OFI) exceeds +2σ in the first 30 min of trading but whose second-half volume share (13:00-close)/Σday is below its 2…"
updated: "2026-04-13T20:11:53"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "threshold_timing_execution"]
ic: "-0.018"
rank_ic: "0.122"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# OrderFlow Imbalance Micro-Trend Exhaustion

## Summary

Stocks whose bid/ask order-flow imbalance (OFI) exceeds +2σ in the first 30 min of trading but whose second-half volume share (13:00-close)/Σday is below its 2…

## Hypothesis

Stocks whose bid/ask order-flow imbalance (OFI) exceeds +2σ in the first 30 min of trading but whose second-half volume share (13:00-close)/Σday is below its 2…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(CSZScore($volume), 0), Greater(CSZScore($volume), 0)), -CSZScore($volume) * CSZScore($volume), 0)```

**Math Formula**: R_{i,t+1}=\begin{cases}-Z_{\text{OFI},i,t}\cdot Z_{\text{Vol},i,t}&\text{if }Z_{\text{OFI},i,t}>0\text{ and }Z_{\text{Vol},i,t}>0\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0180 / 0.1220
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
