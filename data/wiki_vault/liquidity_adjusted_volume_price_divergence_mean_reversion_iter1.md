---
title: "Liquidity-Adjusted Volume-Price Divergence Mean-Reversion"
slug: "liquidity_adjusted_volume_price_divergence_mean_reversion_iter1"
type: "experiment_card"
status: "active"
summary: "Hypothesis: Over 5-day windows, when a stock’s (Close-VWAP)/VWAP diverges from its contemporaneous %-change in turnover while both metrics…"
updated: "2026-04-13T13:52:08.770416"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Volume-Price Divergence Mean-Reversion

## Summary

Hypothesis: Over 5-day windows, when a stock’s (Close-VWAP)/VWAP diverges from its contemporaneous %-change in turnover while both metrics…

## Hypothesis

Hypothesis: Over 5-day windows, when a stock’s (Close-VWAP)/VWAP diverges from its contemporaneous %-change in turnover while both metrics…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Or(Less(Rank(Delta($close,$vwap)/$vwap),0.1),Greater(Rank(Delta($close,$vwap)/$vwap),0.9)),Or(Less(Rank(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)),0.1),Greater(Rank(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)),0.9)),Not(Equal(Sign(Delta($close,$vwap)/$vwap),Sign(Delta($volume*$vwap,5)/Ref($volume*$vwap,5)))),Greater(Delta($open,Ref($close,1))/Ref($close,1),0.5*Std(Delta($open,Ref($close,1)),30))),1,0)```

**Math Formula**: \left\{ r_{i,[t+1,t+3]} = \frac{\text{Close}_{i,t+3}}{\text{Close}_{i,t}} - 1 \right\} \quad \text{with signal} \quad S_{i,t}=1 \;\text{iff}\; \begin{cases} \text{rank}_{t}^{\text{cv}}(i)\in D_{1}\cup D_{10}, \\ \text{rank}_{t}^{\Delta T}(i)\in D_{10}\cup D_{1}, \\ \text{sign}\left(\frac{\text{Close}_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right) \ne \text{sign}\left(\frac{\Delta T_{i,t}}{T_{i,t-5}}\right), \\ \frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}\ge 0.5\sigma_{i,t}^{\text{ON}} \end{cases}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
