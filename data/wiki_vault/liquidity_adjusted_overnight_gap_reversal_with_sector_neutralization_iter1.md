---
title: "Liquidity-Adjusted Overnight Gap Reversal with Sector-Neutralization"
slug: "liquidity_adjusted_overnight_gap_reversal_with_sector_neutralization_iter1"
type: "experiment_card"
status: "failed"
summary: "Go long on stocks that gapped down overnight (Open/Close-1 < 0) yet simultaneously posted the steepest 3-day volume rank decay within their sector; factor = Se…"
updated: "2026-04-13T20:11:39"
tags: ["利用复杂网络与知识图谱挖掘产业链关联的图计算专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0201"
rank_ic: "-0.0072"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Overnight Gap Reversal with Sector-Neutralization

## Summary

Go long on stocks that gapped down overnight (Open/Close-1 < 0) yet simultaneously posted the steepest 3-day volume rank decay within their sector; factor = Se…

## Hypothesis

Go long on stocks that gapped down overnight (Open/Close-1 < 0) yet simultaneously posted the steepest 3-day volume rank decay within their sector; factor = Se…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```CSRank($open / Ref($close,1) - 1) * (-CSRank(Delta($volume,3)))```

**Math Formula**: \text{Signal}_{i,t}=\text{SectorRank}_{s,t}\left(\frac{O_{i,t}}{C_{i,t-1}}-1\right)\;\times\;\left(-\text{SectorRank}_{s,t}\left(\Delta_{3}\text{Vol}_{i,t}\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0201 / -0.0072
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
