---
title: "Hurst-Scaled Liquidity-Weighted Order-Imbalance Reversal"
slug: "hurst_scaled_liquidity_weighted_order_imbalance_reversal_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,18)) * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,1)),Rank($volume),7)) ) goes long (sh…"
updated: "2026-04-14T12:15:58"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0011"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Scaled Liquidity-Weighted Order-Imbalance Reversal

## Summary

Rank( (1-Hurst($close,18)) * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,1)),Rank($volume),7)) ) goes long (sh…

## Hypothesis

Rank( (1-Hurst($close,18)) * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,1)),Rank($volume),7)) ) goes long (sh…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Multiply(Sub(1, CSRank(Ts_Rank(Log($close), 18))), Sign(Delta(Log($close), 3))), Divide(Delta(Log($volume), 1), Log(Mean($volume, 20)))), Sub(1, Corr(CSRank(Delta(Log($close), 1)), CSRank(Delta(Log($volume), 1)), 7))))```

**Math Formula**: \text{Score}_i = \text{Rank}\left(\left(1 - H_i\right) \cdot \text{sgn}\left(\Delta_3 C_i\right) \cdot \frac{\Delta_1 V_i}{\bar{V}_{20,i}} \cdot \left(1 - \rho_{7,i}\right)\right)

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
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
