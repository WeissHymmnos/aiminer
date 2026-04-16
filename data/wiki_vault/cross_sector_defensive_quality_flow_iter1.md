---
title: "Cross-Sector Defensive Quality Flow"
slug: "cross_sector_defensive_quality_flow_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( If( Greater( SectorBetaSPX, 0.9 ), If( Greater( DivYield, SectorMedianDivYield ), Rank( Ts_Mean( Volume, 5 ) / Ts_Mean( Volume, 20 ) ) * Sign( Delta( Clo…"
updated: "2026-04-14T12:08:28"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Cross-Sector Defensive Quality Flow

## Summary

Rank( If( Greater( SectorBetaSPX, 0.9 ), If( Greater( DivYield, SectorMedianDivYield ), Rank( Ts_Mean( Volume, 5 ) / Ts_Mean( Volume, 20 ) ) * Sign( Delta( Clo…

## Hypothesis

Rank( If( Greater( SectorBetaSPX, 0.9 ), If( Greater( DivYield, SectorMedianDivYield ), Rank( Ts_Mean( Volume, 5 ) / Ts_Mean( Volume, 20 ) ) * Sign( Delta( Clo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(Greater(0.9,0.9),Greater($close,Median($close))),Rank(Mean($volume,5)/Mean($volume,20))*Sign(Delta($close,10)),0))```

**Math Formula**: R_{t}=\text{rank}_{\text{sector},t}\left[\mathbb{1}_{\{\beta_{i,t}^{\text{SPX}}>0.9\}}\cdot\mathbb{1}_{\{D_{i,t}>\tilde{D}_{\text{sector},t}\}}\cdot\text{rank}_{\text{sector},t}\left(\frac{\frac{1}{5}\sum_{k=1}^{5}V_{i,t-k+1}}{\frac{1}{20}\sum_{k=1}^{20}V_{i,t-k+1}}\right)\cdot\text{sign}\left(C_{i,t}-C_{i,t-10}\right)\right]

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

- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
