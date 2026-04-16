---
title: "Hurst-Volatility-Adjusted Volume Climax Reversal"
slug: "hurst_volatility_adjusted_volume_climax_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Go long stocks whose 5-day price Hurst < 0.45 (mean-reverting) AND whose 3-day realized volatility ranks in the top-decile while 1-day volume delta ranks in th…"
updated: "2026-04-14T12:01:05"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0043"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Hurst-Volatility-Adjusted Volume Climax Reversal

## Summary

Go long stocks whose 5-day price Hurst < 0.45 (mean-reverting) AND whose 3-day realized volatility ranks in the top-decile while 1-day volume delta ranks in th…

## Hypothesis

Go long stocks whose 5-day price Hurst < 0.45 (mean-reverting) AND whose 3-day realized volatility ranks in the top-decile while 1-day volume delta ranks in th…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less(Ts_Rank($close,5),0.45),Mult(Mult(Neg(Rank(Delta($close,1)/Ref($close,1))),Rank(Delta($volume,1)/Ref($volume,1))),Rank(Std(Delta($close,1)/Ref($close,1),3))),0)```

**Math Formula**: Factor_{i,t}=\mathbb{1}_{H_{i,t}^{(5)}<0.45}\cdot\left(-\text{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-1}}-1\right)\right)\cdot\text{Rank}_{t}\left(\frac{V_{i,t}}{V_{i,t-1}}-1\right)\cdot\text{Rank}_{t}\left(\sigma_{i,t}^{(3)}\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0043 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
