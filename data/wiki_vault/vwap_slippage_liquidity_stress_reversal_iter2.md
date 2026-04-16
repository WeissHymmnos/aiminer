---
title: "VWAP-Slippage Liquidity Stress Reversal"
slug: "vwap_slippage_liquidity_stress_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Abs($close-$vwap)+0.001) * Exp(-Decay(0.1, $volume/Mean($volume,20))) ) goes long stocks whose 1-day price jump is large relative to t…"
updated: "2026-04-14T12:15:26"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0046"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# VWAP-Slippage Liquidity Stress Reversal

## Summary

Rank( Delta($close,1) / (Abs($close-$vwap)+0.001) * Exp(-Decay(0.1, $volume/Mean($volume,20))) ) goes long stocks whose 1-day price jump is large relative to t…

## Hypothesis

Rank( Delta($close,1) / (Abs($close-$vwap)+0.001) * Exp(-Decay(0.1, $volume/Mean($volume,20))) ) goes long stocks whose 1-day price jump is large relative to t…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,1) / (Abs($close - $volume) + 0.001) * Exp(-0.1 * $volume / Mean($volume,20)))```

**Math Formula**: R = \text{Rank}\left( \frac{\Delta C_{t,1}}{|C_t - V_t| + 0.001} \cdot \exp\left(-\lambda \cdot \frac{V_t}{\bar{V}_{t,20}}\right) \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0046 / 0.0000
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
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
