---
title: "Cross-Sectional Residual Reversal After CB Hawkish Shock"
slug: "cross_sectional_residual_reversal_after_cb_hawkish_shock_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank(-1  (Corr(Rank($close/Ref($close,1)), Rank($volume), 5) + 0.5)  (Delta($close,1) / Std($close,20))  If(Rank($vwap/$close)…"
updated: "2026-04-12T07:13:24.749293"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sectional Residual Reversal After CB Hawkish Shock

## Summary

Hypothesis: Rank(-1  (Corr(Rank($close/Ref($close,1)), Rank($volume), 5) + 0.5)  (Delta($close,1) / Std($close,20))  If(Rank($vwap/$close)…

## Hypothesis

Hypothesis: Rank(-1  (Corr(Rank($close/Ref($close,1)), Rank($volume), 5) + 0.5)  (Delta($close,1) / Std($close,20))  If(Rank($vwap/$close)…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Multiply(Const(-1),Add(Corr(Rank(Div($close,Ref($close,1))),Rank($volume),5),Const(0.5))),Divide(Delta($close,1),Std($close,20))),Greater(Rank(Div($vwap,$close)),Const(0.8))))```

**Math Formula**: R_{i,t}=\text{Rank}_t\!\left(\,-1\cdot\left[\,\text{RankCorr}_t\!\left(\,\text{Rank}_t\!\left(\frac{P_{i,t}}{P_{i,t-1}}\right),\;\text{Rank}_t(V_{i,t}),\;5\right)+0.5\,\right]\cdot\frac{P_{i,t}-P_{i,t-1}}{\sigma_{i,t}^{(20)}}\cdot\mathbf{1}\!\left\{\text{Rank}_t\!\left(\frac{\text{VWAP}_{i,t}}{P_{i,t}}\right)>0.8\right\}\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
