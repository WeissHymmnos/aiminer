---
title: "Volatility-Adjusted Overnight Gap with Liquidity Exhaustion"
slug: "volatility_adjusted_overnight_gap_with_liquidity_exhaustion_iter2"
type: "experiment_card"
status: "failed"
summary: "Stocks that gap up overnight (>1%) while 5-day realized vol is in the top quintile and today’s dollar-volume ranks in the bottom quintile versus its 10-day ave…"
updated: "2026-04-13T20:12:00"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.0402"
rank_ic: "0.0143"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Volatility-Adjusted Overnight Gap with Liquidity Exhaustion

## Summary

Stocks that gap up overnight (>1%) while 5-day realized vol is in the top quintile and today’s dollar-volume ranks in the bottom quintile versus its 10-day ave…

## Hypothesis

Stocks that gap up overnight (>1%) while 5-day realized vol is in the top quintile and today’s dollar-volume ranks in the bottom quintile versus its 10-day ave…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater($open/Ref($close,1)-1,0.01),Greater(Std($close,5),Ts_Percentile(Std($close,5),0,80))),-Rank($open/Ref($close,1)-1)*Rank(Std($close,5))*(-Rank($volume/Mean($volume,10)-1)),0)```

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_t\left(\frac{o_{i,t}}{c_{i,t-1}}-1\right)\cdot\text{Rank}_t(\sigma_{i,t}^{(5)})\cdot\left(-\text{Rank}_t\left(\frac{v_{i,t}}{\bar{v}_{i,t}^{(10)}}-1\right)\right)&\text{if }\frac{o_{i,t}}{c_{i,t-1}}-1>0.01\text{ and }\sigma_{i,t}^{(5)}>\Phi_{t}^{(80)}(\sigma^{(5)})\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0402 / 0.0143
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
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
