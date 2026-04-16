---
title: "Overnight-Reversal Gamma Squeeze"
slug: "overnight_reversal_gamma_squeeze_iter1"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Rank( Sign( Ref($close,1)-$open )  Corr( Rank($volume), Rank($close-$vwap), 5 )  ( $high/$low - Ref($high/$low,1) ) ) goes long…"
updated: "2026-04-13T02:13:39.460608"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Overnight-Reversal Gamma Squeeze

## Summary

Hypothesis: Rank( Sign( Ref($close,1)-$open )  Corr( Rank($volume), Rank($close-$vwap), 5 )  ( $high/$low - Ref($high/$low,1) ) ) goes long…

## Hypothesis

Hypothesis: Rank( Sign( Ref($close,1)-$open )  Corr( Rank($volume), Rank($close-$vwap), 5 )  ( $high/$low - Ref($high/$low,1) ) ) goes long…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Sign(Delta($open,1)),Corr(Rank($volume),Rank(Delta($close,$vwap)),5)),Delta(Divide($high,$low),1)))```

**Math Formula**: \text{Signal}_{i,t}=\text{Rank}_{t}\Big(\text{Sign}\big(\text{Ref}(C_{i,t},1)-O_{i,t}\big)\cdot\text{Corr}_{k=0..4}\big(\text{Rank}(V_{i,t-k}),\text{Rank}(C_{i,t-k}-\text{VWAP}_{i,t-k}),5\big)\cdot\big(\frac{H_{i,t}}{L_{i,t}}-\text{Ref}(\frac{H_{i,t}}{L_{i,t}},1)\big)\Big)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
