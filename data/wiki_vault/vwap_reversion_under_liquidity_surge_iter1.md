---
title: "VWAP-Reversion Under Liquidity Surge"
slug: "vwap_reversion_under_liquidity_surge_iter1"
type: "experiment_card"
status: "active"
summary: "Stocks that close below VWAP but experience an abrupt 1-day volume spike while showing negative 5-day momentum tend to revert upward next day; factor = Rank(Re…"
updated: "2026-04-13T20:11:28"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.051"
rank_ic: "0.142"
iteration: "1"
is_effective: "true"
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

# VWAP-Reversion Under Liquidity Surge

## Summary

Stocks that close below VWAP but experience an abrupt 1-day volume spike while showing negative 5-day momentum tend to revert upward next day; factor = Rank(Re…

## Hypothesis

Stocks that close below VWAP but experience an abrupt 1-day volume spike while showing negative 5-day momentum tend to revert upward next day; factor = Rank(Re…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta(Ref($close,1),Ref($vwap,1))/Ref($vwap,1))*Rank(Delta(Ref($volume,1),Ref($volume,2))/Ref($volume,2))*(-Rank(Ts_Percentile($close,5)/Ref($close,1)-1))```

**Math Formula**: F_{i,t}=\text{Rank}_{i,t-1}\left(\frac{C_{i,t-1}-VWAP_{i,t-1}}{VWAP_{i,t-1}}\right)\cdot\text{Rank}_{i,t-1}\left(\frac{V_{i,t-1}-V_{i,t-2}}{V_{i,t-2}}\right)\cdot\left(-\text{Rank}_{i,t-1}\left(\frac{\min_{k=1..5}C_{i,t-k}}{C_{i,t-1}}-1\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0510 / 0.1420
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
