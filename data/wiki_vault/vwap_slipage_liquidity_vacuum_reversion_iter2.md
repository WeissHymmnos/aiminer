---
title: "VWAP-Slipage Liquidity Vacuum Reversion"
slug: "vwap_slipage_liquidity_vacuum_reversion_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)*Abs($close-$vwap)+1e-6) * Sign(Corr($volume,$close-$vwap,3)) ) goes long stocks whose 1-day price change is large relat…"
updated: "2026-04-14T12:08:47"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0055"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# VWAP-Slipage Liquidity Vacuum Reversion

## Summary

Rank( Delta($close,1) / (Std($volume,5)*Abs($close-$vwap)+1e-6) * Sign(Corr($volume,$close-$vwap,3)) ) goes long stocks whose 1-day price change is large relat…

## Hypothesis

Rank( Delta($close,1) / (Std($volume,5)*Abs($close-$vwap)+1e-6) * Sign(Corr($volume,$close-$vwap,3)) ) goes long stocks whose 1-day price change is large relat…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,1) / (Std($volume,5) * Abs($close - $vwap) + 1e-6) * Sign(Corr($volume,Abs($close - $vwap),3)))```

**Math Formula**: R_{t}=\text{Rank}\left(\frac{\Delta P_{t,1}}{\left(\sigma_{V,t,5}\cdot|P_{t}-VWAP_{t}|+10^{-6}\right)}\cdot\text{Sign}\left(\rho_{t,3}\left(V,|P-VWAP|\right)\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0055 / 0.0000
- **Effectiveness:** ✅ effective

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
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
