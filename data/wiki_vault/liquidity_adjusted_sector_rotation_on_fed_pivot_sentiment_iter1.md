---
title: "Liquidity-Adjusted Sector Rotation on Fed-Pivot Sentiment"
slug: "liquidity_adjusted_sector_rotation_on_fed_pivot_sentiment_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($volume,5) / Delta($volume,20))  Sign(Corr(Rank($close / Ref($close,5)), FedFundsFutChange, 15))  If(Rank($close /…"
updated: "2026-04-13T02:13:40.046361"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Sector Rotation on Fed-Pivot Sentiment

## Summary

Hypothesis: Rank( (Delta($volume,5) / Delta($volume,20))  Sign(Corr(Rank($close / Ref($close,5)), FedFundsFutChange, 15))  If(Rank($close /…

## Hypothesis

Hypothesis: Rank( (Delta($volume,5) / Delta($volume,20))  Sign(Corr(Rank($close / Ref($close,5)), FedFundsFutChange, 15))  If(Rank($close /…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($volume,5) / Delta($volume,20) * Sign(Corr(Rank($close / Ref($close,5)), Delta($close,1), 15)) * If(Less(Rank($close / Ref($close,20)),0.4),1,0) - If(Greater(Rank($close / Ref($close,20)),0.4),1,0))```

**Math Formula**: \text{Signal}_{i,t}=\operatorname{Rank}_{t}\left(\frac{\Delta_{5}V_{i,t}}{\Delta_{20}V_{i,t}}\cdot\operatorname{Sign}\left(\operatorname{Corr}_{15}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-5}}\right),\Delta F_{t}\right)\right)\cdot\mathbf{1}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-20}}\right)<0.4\right)-\mathbf{1}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-20}}\right)\geq 0.4\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

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
