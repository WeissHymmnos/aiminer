---
title: "Liquidity-Adjusted Overnight Gap Reversal with Asymmetric Volume Confirmation"
slug: "liquidity_adjusted_overnight_gap_reversal_with_asymmetric_volume_confirmation_iter2"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up >0.5% overnight on a day when their cancelled-order ratio (cancelled/shares-traded) spikes above its 5-day 80th-percentile band, but the fol…"
updated: "2026-04-13T20:12:11"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.026"
rank_ic: "0.008"
iteration: "2"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Adjusted Overnight Gap Reversal with Asymmetric Volume Confirmation

## Summary

Stocks that gap up >0.5% overnight on a day when their cancelled-order ratio (cancelled/shares-traded) spikes above its 5-day 80th-percentile band, but the fol…

## Hypothesis

Stocks that gap up >0.5% overnight on a day when their cancelled-order ratio (cancelled/shares-traded) spikes above its 5-day 80th-percentile band, but the fol…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Less(Ts_Percentile($volume,5,50),Ref(Ts_Percentile($volume,5,50),1)),Greater(Delta($open,$close)/Ref($close,1),0.005)),-1*CSRank(Delta($open,$close)/Ref($close,1))*CSRank(Delta($volume,5)-Ts_Percentile(Delta($volume,5),5,80)),0)```

**Math Formula**: Factor_t = -\text{Rank}(\text{OpenGap}_t) \cdot \text{Rank}(\Delta\text{CancelRatio}_{t,5}) \cdot \mathbb{1}_{\left\{\text{T0\_30min\_Volume}_t < \text{Median}_{k=1}^5(\text{T0\_30min\_Volume}_{t-k})\right\}} \cdot \mathbb{1}_{\left\{\text{OpenGap}_t > 0.005\right\}}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0260 / 0.0080
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[implementation_drift_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
