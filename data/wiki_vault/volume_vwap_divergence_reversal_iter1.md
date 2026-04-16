---
title: "Volume-VWAP Divergence Reversal"
slug: "volume_vwap_divergence_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Go long stocks whose intraday close is below VWAP but where the rolling 5-day correlation between ranked volume and ranked (Clo…"
updated: "2026-04-13T13:52:07.246519"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "long_only_selection_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "long_only_selection_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "long_only_selection_execution"]
related_experiments: []
---

# Volume-VWAP Divergence Reversal

## Summary

Hypothesis: Go long stocks whose intraday close is below VWAP but where the rolling 5-day correlation between ranked volume and ranked (Clo…

## Hypothesis

Hypothesis: Go long stocks whose intraday close is below VWAP but where the rolling 5-day correlation between ranked volume and ranked (Clo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```-Rank(Corr(CSRank($volume), CSRank(($close - $vwap) / $vwap), 5)) * Sign($close - $vwap)```

**Math Formula**: \text{Factor}_{t} = -\text{Rank}_{\text{all } i}\left(\text{Corr}_{\tau=t-4}^{t}\left(\text{Rank}(V_{i,\tau}),\;\text{Rank}\left(\frac{C_{i,\tau}-\text{VWAP}_{i,\tau}}{\text{VWAP}_{i,\tau}}\right)\right)\right)\;\cdot\;\text{Sign}(C_{i,t}-\text{VWAP}_{i,t})

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
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[long_only_selection_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
