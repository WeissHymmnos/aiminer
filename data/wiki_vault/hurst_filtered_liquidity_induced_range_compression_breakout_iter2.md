---
title: "Hurst-Filtered Liquidity-Induced Range Compression Breakout"
slug: "hurst_filtered_liquidity_induced_range_compression_breakout_iter2"
type: "experiment_card"
status: "failed"
summary: "Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Ts_Rank($close,3)-0.5) * (1-Corr(Rank($close/Ref($close,10)),Rank($volume),7)) * (Ts_Max($high,5)-Ts_Min($lo…"
updated: "2026-04-14T12:08:58"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0006"
rank_ic: "0.0"
iteration: "2"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Liquidity-Induced Range Compression Breakout

## Summary

Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Ts_Rank($close,3)-0.5) * (1-Corr(Rank($close/Ref($close,10)),Rank($volume),7)) * (Ts_Max($high,5)-Ts_Min($lo…

## Hypothesis

Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Ts_Rank($close,3)-0.5) * (1-Corr(Rank($close/Ref($close,10)),Rank($volume),7)) * (Ts_Max($high,5)-Ts_Min($lo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(GreaterEqual(Ts_Rank($close,21),0.45),LessEqual(Ts_Rank($close,21),0.7)),1,0)*Sign(Ts_Rank($close,3)-0.5)*(1-Corr(Rank($close/Ref($close,10)),Rank($volume),7))*(Ts_Max($high,5)-Ts_Min($low,5))/Ref($close,5))```

**Math Formula**: R=\operatorname{Rank}\Bigl(\mathbf{1}_{[0.45,0.7]}\!igl(H_{21}(C)\bigr)\cdot\operatorname{Sign}\!igl(r_{3}(C)-0.5\bigr)\cdot\bigl(1-\rho_{7}\bigl(\operatorname{Rank}(C/C_{-10}),\operatorname{Rank}(V)\bigr)\bigr)\cdot\frac{\max_{5}(H)-\min_{5}(L)}{C_{-5}}\Bigr)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0006 / 0.0000
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
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
