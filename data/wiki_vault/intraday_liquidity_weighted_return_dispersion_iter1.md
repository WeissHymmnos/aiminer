---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( ( ($close - $open) / ($high - $low + 1e-6) ) * ( $volume / Ts_Mean($volume,10) ) * Sign( Corr($vwap, $close, 5) - Corr($vwap, $close, 20) ) )"
updated: "2026-04-14T12:15:01"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Intraday Liquidity-Weighted Return Dispersion

## Summary

Rank( ( ($close - $open) / ($high - $low + 1e-6) ) * ( $volume / Ts_Mean($volume,10) ) * Sign( Corr($vwap, $close, 5) - Corr($vwap, $close, 20) ) )

## Hypothesis

Rank( ( ($close - $open) / ($high - $low + 1e-6) ) * ( $volume / Ts_Mean($volume,10) ) * Sign( Corr($vwap, $close, 5) - Corr($vwap, $close, 20) ) )

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Mult(Div(Delta($close,0),Delta($high,0)-Delta($low,0)+1e-6),Div($volume,Mean($volume,10))),Mult(Sign(Delta(Corr($vwap,$close,5),Corr($vwap,$close,20))),1))```

**Math Formula**: \text{Rank}\left(\left(\frac{C_t - O_t}{H_t - L_t + 10^{-6}}\right)\cdot\left(\frac{V_t}{\frac{1}{10}\sum_{k=0}^{9}V_{t-k}}\right)\cdot\text{Sign}\left(\text{Corr}(\text{VWAP}_{t-4:t},C_{t-4:t}) - \text{Corr}(\text{VWAP}_{t-19:t},C_{t-19:t})\right)\right)

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

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
