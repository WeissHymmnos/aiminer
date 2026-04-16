---
title: "Hurst-Filtered Liquidity-Volatility Divergence Reversal"
slug: "hurst_filtered_liquidity_volatility_divergence_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( If(Hurst($close,30)∈[0.3,0.55], -1, 0) * Sign(Delta($close,2)) * (Std($volume,5)/Mean($volume,20)-1) * (1-Corr(Rank(Delta($close,1)),Rank(Delta($volume,1…"
updated: "2026-04-14T12:08:25"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0011"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Liquidity-Volatility Divergence Reversal

## Summary

Rank( If(Hurst($close,30)∈[0.3,0.55], -1, 0) * Sign(Delta($close,2)) * (Std($volume,5)/Mean($volume,20)-1) * (1-Corr(Rank(Delta($close,1)),Rank(Delta($volume,1…

## Hypothesis

Rank( If(Hurst($close,30)∈[0.3,0.55], -1, 0) * Sign(Delta($close,2)) * (Std($volume,5)/Mean($volume,20)-1) * (1-Corr(Rank(Delta($close,1)),Rank(Delta($volume,1…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Multiply(If(And(GreaterEqual(Ts_Rank($close,30),0.3),LessEqual(Ts_Rank($close,30),0.55)),-1,0),Sign(Delta($close,2))),Subtract(Divide(Std($volume,5),Mean($volume,20)),1)),Subtract(1,Corr(Rank(Delta($close,1)),Rank(Delta($volume,1)),10))))```

**Math Formula**: R=\operatorname{Rank}\left(\left[\mathbb{1}_{[0.3,0.55]}\left(H_{30}\right)\cdot(-1)\right]\cdot\operatorname{sgn}\left(\Delta_{2}P\right)\cdot\left(\frac{\sigma_{5}V}{\mu_{20}V}-1\right)\cdot\left(1-\rho_{10}\left(\operatorname{Rank}(\Delta_{1}P),\operatorname{Rank}(\Delta_{1}V)\right)\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0011 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
