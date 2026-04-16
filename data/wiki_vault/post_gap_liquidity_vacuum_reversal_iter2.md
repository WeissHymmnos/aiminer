---
title: "Post-Gap Liquidity Vacuum Reversal"
slug: "post_gap_liquidity_vacuum_reversal_iter2"
type: "experiment_card"
status: "active"
summary: "After an overnight gap >1%, if the first-hour consolidated tape shows both (i) a top-quintile drop in visible depth on the bid side and (ii) a bottom-quintile…"
updated: "2026-04-13T20:12:11"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.034"
rank_ic: "0.14"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Post-Gap Liquidity Vacuum Reversal

## Summary

After an overnight gap >1%, if the first-hour consolidated tape shows both (i) a top-quintile drop in visible depth on the bid side and (ii) a bottom-quintile…

## Hypothesis

After an overnight gap >1%, if the first-hour consolidated tape shows both (i) a top-quintile drop in visible depth on the bid side and (ii) a bottom-quintile…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(Delta($open,1),0.01),-1*Rank(Delta($open,1))*Rank(Delta($volume,1))*Rank(Delta($volume,1)),0)```

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_{\text{cross}}\left(\frac{O_{i,t}}{C_{i,t-1}}-1\right)\cdot\text{Rank}_{\text{cross}}\left(-\Delta\text{BidDepth}_{i,t}^{09:30-10:30}\right)\cdot\text{Rank}_{\text{cross}}\left(\frac{\text{SellCancel}_{i,t}^{09:30-10:30}}{\text{BuyCancel}_{i,t}^{09:30-10:30}}\right)&\text{if }\frac{O_{i,t}}{C_{i,t-1}}-1>0.01\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0340 / 0.1400
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
