---
title: "Volume-Weighted Intraday Gradient Reversal"
slug: "volume_weighted_intraday_gradient_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5) + 1e-6) * Exp(-Abs(Delta($vwap/$close,1))) ) goes long (short) stocks whose 1-day close change is large relative to the…"
updated: "2026-04-14T12:25:51"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Volume-Weighted Intraday Gradient Reversal

## Summary

Rank( Delta($close,1) / (Std($volume,5) + 1e-6) * Exp(-Abs(Delta($vwap/$close,1))) ) goes long (short) stocks whose 1-day close change is large relative to the…

## Hypothesis

Rank( Delta($close,1) / (Std($volume,5) + 1e-6) * Exp(-Abs(Delta($vwap/$close,1))) ) goes long (short) stocks whose 1-day close change is large relative to the…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mul(Div(Delta($close,1),Add(Std($volume,5),0.000001)),Exp(Neg(Abs(Delta(Div($vwap,$close),1)))))))```

**Math Formula**: R_{t} = \text{rank}_{i}\left(\frac{\Delta P_{i,t}}{\sigma_{V_{i},5,t}+10^{-6}}\cdot\exp\left(-\left|\Delta\left(\frac{VWAP_{i,t}}{P_{i,t}}\right)\right|\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ✅ effective

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
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
