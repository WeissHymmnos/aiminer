---
title: "Cross-Sector Liquidity Rotation Reversal"
slug: "cross_sector_liquidity_rotation_reversal_iter1"
type: "experiment_card"
status: "active"
summary: "Stocks that outperform their sector by >1% on a 5-day basis while contemporaneous sector-level money-flow (sum of dollar-volume) drops >2% reverse next-day; fa…"
updated: "2026-04-13T20:11:57"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.045"
rank_ic: "0.064"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sector Liquidity Rotation Reversal

## Summary

Stocks that outperform their sector by >1% on a 5-day basis while contemporaneous sector-level money-flow (sum of dollar-volume) drops >2% reverse next-day; fa…

## Hypothesis

Stocks that outperform their sector by >1% on a 5-day basis while contemporaneous sector-level money-flow (sum of dollar-volume) drops >2% reverse next-day; fa…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(Delta($close,5)-Delta(Mean($close,1),5),0.01),Less(Delta(Mean($volume*$close,1),5)/Ref(Mean($volume*$close,1),5),-0.02)),-Rank(Delta($close,5)-Delta(Mean($close,1),5))*Rank(Delta(Mean($volume*$close,1),5)),0)```

**Math Formula**: \text{Factor}_{t}=\begin{cases}-\text{Rank}\left(\frac{\text{Close}_{i,t}}{\text{Close}_{i,t-5}}-\frac{\text{Close}_{\text{sector},t}}{\text{Close}_{\text{sector},t-5}}\right)\cdot\text{Rank}\left(\text{SectorDollarVolume}_{t}-\text{SectorDollarVolume}_{t-5}\right),&\text{if }\frac{\text{Close}_{i,t}}{\text{Close}_{i,t-5}}-\frac{\text{Close}_{\text{sector},t}}{\text{Close}_{\text{sector},t-5}}>0.01\text{ and }\frac{\text{SectorDollarVolume}_{t}-\text{SectorDollarVolume}_{t-5}}{\text{SectorDollarVolume}_{t-5}}<-0.02\\0,&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0450 / 0.0640
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
