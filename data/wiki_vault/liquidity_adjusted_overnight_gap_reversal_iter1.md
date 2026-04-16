---
title: "Liquidity-Adjusted Overnight Gap Reversal"
slug: "liquidity_adjusted_overnight_gap_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-Ref($open,1)) / Ref($close,2)  (1 / (1+Rank($volume/Ref($volume,1))))  Sign(Mean($close,5)-$close) ) goes…"
updated: "2026-04-13T02:13:36.889569"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Adjusted Overnight Gap Reversal

## Summary

Hypothesis: Rank( (Ref($close,1)-Ref($open,1)) / Ref($close,2)  (1 / (1+Rank($volume/Ref($volume,1))))  Sign(Mean($close,5)-$close) ) goes…

## Hypothesis

Hypothesis: Rank( (Ref($close,1)-Ref($open,1)) / Ref($close,2)  (1 / (1+Rank($volume/Ref($volume,1))))  Sign(Mean($close,5)-$close) ) goes…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),Ref($open,1)),Ref($close,2)),Divide(1,Add(1,Rank(Divide($volume,Ref($volume,1)))))),Sign(Delta(Mean($close,5),$close))))```

**Math Formula**: \text{Signal}_t = \text{Rank}\left( \frac{\text{Ref}(C_t,1) - \text{Ref}(O_t,1)}{\text{Ref}(C_t,2)} \cdot \frac{1}{1 + \text{Rank}\left(\frac{V_t}{\text{Ref}(V_t,1)}\right)} \cdot \text{Sign}\left(\frac{1}{5}\sum_{i=0}^{4} \text{Ref}(C_t,i) - C_t\right) \right)

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
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
