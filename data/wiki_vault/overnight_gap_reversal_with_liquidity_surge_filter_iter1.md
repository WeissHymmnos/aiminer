---
title: "Overnight Gap Reversal with Liquidity Surge Filter"
slug: "overnight_gap_reversal_with_liquidity_surge_filter_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5% Open/PrevClose) but experience a same-day surge in lit-depth (top-decile Δ(VisibleBidVolume,1)) tend to mean-revert intrada…"
updated: "2026-04-13T20:11:35"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.016"
rank_ic: "0.034"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Overnight Gap Reversal with Liquidity Surge Filter

## Summary

Stocks that gap up overnight (>1.5% Open/PrevClose) but experience a same-day surge in lit-depth (top-decile Δ(VisibleBidVolume,1)) tend to mean-revert intrada…

## Hypothesis

Stocks that gap up overnight (>1.5% Open/PrevClose) but experience a same-day surge in lit-depth (top-decile Δ(VisibleBidVolume,1)) tend to mean-revert intrada…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(Delta($open,1)/Ref($close,1),0.015),-Rank(Delta($open,1)/Ref($close,1))*Rank(Delta($volume,1))*Rank($high-$open),0)```

**Math Formula**: F_{t}=\begin{cases}-\text{Rank}\left(\frac{O_{t}}{C_{t-1}}-1\right)\cdot\text{Rank}\left(\Delta V_{t}^{\text{lit}}\right)\cdot\text{Rank}\left(H_{t}-O_{t}\right),&\text{if }\frac{O_{t}}{C_{t-1}}-1>0.015\\0,&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0160 / 0.0340
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

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
