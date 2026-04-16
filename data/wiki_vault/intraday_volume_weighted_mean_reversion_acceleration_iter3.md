---
title: "Intraday Volume-Weighted Mean Reversion Acceleration"
slug: "intraday_volume_weighted_mean_reversion_acceleration_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)+1e-6) * Sign(Corr($vwap,$close,3)) * (1-Abs(Corr($close,$volume,3))) ) goes long stocks whose 1-day price change is lar…"
updated: "2026-04-14T12:15:47"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0044"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Intraday Volume-Weighted Mean Reversion Acceleration

## Summary

Rank( Delta($close,1) / (Std($volume,5)+1e-6) * Sign(Corr($vwap,$close,3)) * (1-Abs(Corr($close,$volume,3))) ) goes long stocks whose 1-day price change is lar…

## Hypothesis

Rank( Delta($close,1) / (Std($volume,5)+1e-6) * Sign(Corr($vwap,$close,3)) * (1-Abs(Corr($close,$volume,3))) ) goes long stocks whose 1-day price change is lar…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,1) / (Std($volume,5) + 0.000001) * Sign(Corr($vwap,$close,3)) * (1 - Abs(Corr($close,$volume,3))))```

**Math Formula**: \text{Signal}_i = \text{Rank}\left( \frac{\Delta P_{i,1}}{\sigma_{V_i,5}+10^{-6}} \cdot \text{Sign}\left(\rho_{i}^{(PV,3)}\right) \cdot \left(1 - \left|\rho_{i}^{(CP,3)}\right|\right) \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0044 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
