---
title: "Cap-Adjusted Liquidity Shock Reversal on Trade-Weighted Dollar Spikes"
slug: "cap_adjusted_liquidity_shock_reversal_on_trade_weighted_dollar_spikes_iter2"
type: "experiment_card"
status: "failed"
summary: "Go long (short) stocks that fell (rose) on 3-day volume >90th percentile while exhibiting above-median 5-day sensitivity to DXY upside, but only for large-cap…"
updated: "2026-04-14T12:08:59"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Cap-Adjusted Liquidity Shock Reversal on Trade-Weighted Dollar Spikes

## Summary

Go long (short) stocks that fell (rose) on 3-day volume >90th percentile while exhibiting above-median 5-day sensitivity to DXY upside, but only for large-cap…

## Hypothesis

Go long (short) stocks that fell (rose) on 3-day volume >90th percentile while exhibiting above-median 5-day sensitivity to DXY upside, but only for large-cap…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```CSRank(Ref($close,-1)/$close-1) * Sign(1) * (-Sign(Log($close/Ref($close,3))) * If(Greater(Sum($volume,3),Ts_Percentile(Sum($volume,3),1,90)),1,0) * If(Greater(Corr($close,Ref($close,-1),5),Ts_Percentile(Corr($close,Ref($close,-1),5),1,50)),1,0) * If(Greater($close,Ts_Percentile($close,1,80)),1,0) * If(Greater(Delta($close,21),0),1,0))```

**Math Formula**: R_{i,t+1}=\text{sign}\left(\text{IC}_{\text{hist}}\right)\cdot\left[-\text{sign}\left(r_{i,t}^{(3)}\right)\cdot\mathbb{1}\left(V_{i,t}^{(3)}>Q_{0.90}\left(V_{\cdot,t}^{(3)}\right)\right)\cdot\mathbb{1}\left(\beta_{i,t}^{DXY\uparrow}>\text{median}_{j}\left(\beta_{j,t}^{DXY\uparrow}\right)\right)\cdot\mathbb{1}\left(\text{cap}_{i,t}>Q_{0.80}\left(\text{cap}_{\cdot,t}\right)\right)\cdot\mathbb{1}\left(\Delta\text{ImpCost}_{s(i),t}>0\right)\right]

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
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

## Next Steps

Promote or refine after collecting stronger evidence.
