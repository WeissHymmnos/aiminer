---
title: "Liquidity-Divergent Pairs Spillover Reversal"
slug: "liquidity_divergent_pairs_spillover_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Among sector-neutral pairs pre-selected by 20-day cointegration, the leg whose intraday VWAP momentum diverges most negatively from its 5-day liquidity rank (i…"
updated: "2026-04-13T20:12:11"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0012"
rank_ic: "0.0133"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Divergent Pairs Spillover Reversal

## Summary

Among sector-neutral pairs pre-selected by 20-day cointegration, the leg whose intraday VWAP momentum diverges most negatively from its 5-day liquidity rank (i…

## Hypothesis

Among sector-neutral pairs pre-selected by 20-day cointegration, the leg whose intraday VWAP momentum diverges most negatively from its 5-day liquidity rank (i…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(Delta($vwap,1),0),Greater(Delta(Ref($vwap,1),1),0)),Rank(Delta($vwap,1)),0) * (-Rank(Delta(Ts_Rank($volume,5),5))) / Abs(CSRank($close))```

**Math Formula**: F_{i,t}=\frac{1}{z_{p,t}}\cdot\mathbb{1}_{i=\arg\max_{j\in p}\Delta\text{VWAP}_{j,t}}\cdot\text{Rank}_{\mathcal{S}_t}\bigl(\Delta\text{VWAP}_{i,t}\bigr)\cdot\Bigl(-\text{Rank}_{\mathcal{S}_t}\bigl(\Delta\text{Vol}_{i,t}^{(5)}\bigr)\Bigr)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0012 / 0.0133
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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
