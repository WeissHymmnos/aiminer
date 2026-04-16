---
title: "Liquidity-Contrarian Overnight Gap Mean-Reversion"
slug: "liquidity_contrarian_overnight_gap_mean_reversion_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up overnight on sharply shrinking volume tend to mean-revert intraday; factor = -Rank((Open-PrevClose)/PrevClose) * Rank((PrevVolume-Ref(PrevVo…"
updated: "2026-04-13T20:11:34"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0195"
rank_ic: "-0.0037"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Contrarian Overnight Gap Mean-Reversion

## Summary

Stocks that gap up overnight on sharply shrinking volume tend to mean-revert intraday; factor = -Rank((Open-PrevClose)/PrevClose) * Rank((PrevVolume-Ref(PrevVo…

## Hypothesis

Stocks that gap up overnight on sharply shrinking volume tend to mean-revert intraday; factor = -Rank((Open-PrevClose)/PrevClose) * Rank((PrevVolume-Ref(PrevVo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```-Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank((Ref($volume,1) - Ref($volume,5)) / Ref($volume,5))```

**Math Formula**: R_{i,t}=\alpha+\beta F_{i,t}+\varepsilon_{i,t}\quad\text{with}\quad F_{i,t}=-\text{Rank}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\text{Rank}\left(\frac{V_{i,t-1}-V_{i,t-6}}{V_{i,t-6}}\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0195 / -0.0037
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
