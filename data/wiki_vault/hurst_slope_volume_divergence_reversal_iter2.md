---
title: "Hurst-Slope Volume Divergence Reversal"
slug: "hurst_slope_volume_divergence_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank the product of (-Rank(ts_slope(HurstPrice,3),5)) * (-Rank(ts_slope(HurstVolume,3),3)) * (-Rank((VWAP-Close)/Close)) to target stocks whose price persisten…"
updated: "2026-04-13T20:11:53"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.015"
rank_ic: "0.067"
iteration: "2"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Slope Volume Divergence Reversal

## Summary

Rank the product of (-Rank(ts_slope(HurstPrice,3),5)) * (-Rank(ts_slope(HurstVolume,3),3)) * (-Rank((VWAP-Close)/Close)) to target stocks whose price persisten…

## Hypothesis

Rank the product of (-Rank(ts_slope(HurstPrice,3),5)) * (-Rank(ts_slope(HurstVolume,3),3)) * (-Rank((VWAP-Close)/Close)) to target stocks whose price persisten…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Neg(Rank(Divide(Delta($close,3),3),5)),Neg(Rank(Divide(Delta($volume,3),3),3))),Neg(Rank(Divide(Delta($vwap,$close),$close),N))))```

**Math Formula**: R = \text{Rank}\left( -\text{Rank}\left( \frac{\text{HurstPrice}_{t}-\text{HurstPrice}_{t-3}}{3},5\right) \cdot -\text{Rank}\left( \frac{\text{HurstVolume}_{t}-\text{HurstVolume}_{t-3}}{3},3\right) \cdot -\text{Rank}\left( \frac{\text{VWAP}-\text{Close}}{\text{Close}},N\right) \right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0150 / 0.0670
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
