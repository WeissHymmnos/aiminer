---
title: "Hurst_Oil_Momentum_Reversal"
slug: "hurst_oil_momentum_reversal_iter2"
type: "experiment_card"
status: "active"
summary: "Hypothesis: When WTI 60-day Hurst exponent drops below 0.45 (signalling mean-reversion regime) AND the 5-day RSI of front-month Brent excee…"
updated: "2026-04-12T14:38:07.999162"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "market_regime_base", "implementation_drift_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution", "volume_divergence_signal"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["implementation_drift_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst_Oil_Momentum_Reversal

## Summary

Hypothesis: When WTI 60-day Hurst exponent drops below 0.45 (signalling mean-reversion regime) AND the 5-day RSI of front-month Brent excee…

## Hypothesis

Hypothesis: When WTI 60-day Hurst exponent drops below 0.45 (signalling mean-reversion regime) AND the 5-day RSI of front-month Brent excee…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less(Ts_Rank(Log($close), 60), 0.45), If(Greater(EMA(Greater(Ref($close, 1), $close), 5) / EMA(Abs(Delta($close, 1)), 5) * 100, 70), If(Greater(Corr(Delta($close, 1), Delta(Ref($close, 1), 1), 20), Ts_Percentile(Corr(Delta($close, 1), Delta(Ref($close, 1), 1), 20), 20, 80)), 1, 0), 0), 0)```

**Math Formula**: \text{Signal}_t = \mathbf{1}_{\{H_{60,t}^{\text{WTI}} < 0.45\}} \cdot \mathbf{1}_{\{\text{RSI}_{5,t}^{\text{Brent}} > 70\}} \cdot \mathbf{1}_{\{\beta_{20,t}^{\text{stock}} \geq F_{0.80}(\beta_{20,t}^{\text{univ}})\}}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[implementation_drift_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
