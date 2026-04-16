---
title: "Liquidity Vacuum Gap Reversal"
slug: "liquidity_vacuum_gap_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)+1e-6) * (1-Abs(Corr($vwap,$close,3))) * Sign(Delta($volume,1)) ) goes long (short) stocks that printed an outsized 1-da…"
updated: "2026-04-14T12:08:23"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0042"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity Vacuum Gap Reversal

## Summary

Rank( Delta($close,1) / (Std($volume,5)+1e-6) * (1-Abs(Corr($vwap,$close,3))) * Sign(Delta($volume,1)) ) goes long (short) stocks that printed an outsized 1-da…

## Hypothesis

Rank( Delta($close,1) / (Std($volume,5)+1e-6) * (1-Abs(Corr($vwap,$close,3))) * Sign(Delta($volume,1)) ) goes long (short) stocks that printed an outsized 1-da…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,1) / (Std($volume,5) + 1e-6) * (1 - Abs(Corr($close,$vwap,3))) * Sign(Delta($volume,1)))```

**Math Formula**: R = \text{rank}\left( \frac{\Delta P_{t}}{\sigma_{V,5}+10^{-6}} \cdot \left(1-\left|\rho_{3}(P,VWAP)\right|\right) \cdot \text{sign}\left(\Delta V_{t}\right) \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0042 / 0.0000
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
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
