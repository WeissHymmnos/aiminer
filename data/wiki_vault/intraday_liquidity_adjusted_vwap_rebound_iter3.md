---
title: "Intraday Liquidity-Adjusted VWAP Rebound"
slug: "intraday_liquidity_adjusted_vwap_rebound_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($vwap,1) / (Std($volume,5)+1e3) * Sign(Corr($close,$volume,2)) * Power(-1,Sign(Delta($close,1))) ) goes long stocks whose VWAP moved sharply on low…"
updated: "2026-04-14T12:09:11"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0085"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Intraday Liquidity-Adjusted VWAP Rebound

## Summary

Rank( Delta($vwap,1) / (Std($volume,5)+1e3) * Sign(Corr($close,$volume,2)) * Power(-1,Sign(Delta($close,1))) ) goes long stocks whose VWAP moved sharply on low…

## Hypothesis

Rank( Delta($vwap,1) / (Std($volume,5)+1e3) * Sign(Corr($close,$volume,2)) * Power(-1,Sign(Delta($close,1))) ) goes long stocks whose VWAP moved sharply on low…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Delta($vwap,1),Add(Std($volume,5),0.001)),Sign(Corr($close,$volume,2))),If(Greater(Delta($close,1),0),-1,1)))```

**Math Formula**: R = \text{rank}\left( \frac{v_t - v_{t-1}}{\sigma(V,5)_t + 10^{-3}} \cdot \text{sgn}\left(\rho(C,V,2)_t\right) \cdot (-1)^{\text{sgn}(C_t - C_{t-1})} \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0085 / 0.0000
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
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
