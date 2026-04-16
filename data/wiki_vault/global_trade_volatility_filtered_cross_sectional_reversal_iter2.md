---
title: "Global-Trade-Volatility-Filtered Cross-Sectional Reversal"
slug: "global_trade_volatility_filtered_cross_sectional_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( -Delta(Close,5) * Pow(Corr(Delta(Close,3), Delta(BalticDryIndex,3), 15),2) * (1+RANK(ExportWeight)) ) captures stocks that have fallen hardest in the las…"
updated: "2026-04-14T12:15:25"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0108"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Global-Trade-Volatility-Filtered Cross-Sectional Reversal

## Summary

Rank( -Delta(Close,5) * Pow(Corr(Delta(Close,3), Delta(BalticDryIndex,3), 15),2) * (1+RANK(ExportWeight)) ) captures stocks that have fallen hardest in the las…

## Hypothesis

Rank( -Delta(Close,5) * Pow(Corr(Delta(Close,3), Delta(BalticDryIndex,3), 15),2) * (1+RANK(ExportWeight)) ) captures stocks that have fallen hardest in the las…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Neg(Delta($close,5)),Multiply(Corr(Delta($close,3),Delta($close,3),15),Corr(Delta($close,3),Delta($close,3),15))),Add(1,Rank($volume))))```

**Math Formula**: R_i = \text{rank}_t\left( -\Delta P_{i,t}^{(5)} \cdot \left[ \text{corr}_{\tau=15}\left( \Delta P_{i,\tau}^{(3)}, \Delta B_{\tau}^{(3)} \right) \right]^2 \cdot \left( 1 + \text{rank}_t\left( W_{i,t}^{\text{exp}} \right) \right) \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0108 / 0.0000
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
