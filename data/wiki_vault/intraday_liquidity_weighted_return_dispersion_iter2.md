---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter2"
type: "experiment_card"
status: "active"
summary: "Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 5 ) * Sign( Mean($close,3) - Mean($vwap,3) ) )"
updated: "2026-04-14T12:33:10"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.087"
rank_ic: "0.075"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Intraday Liquidity-Weighted Return Dispersion

## Summary

Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 5 ) * Sign( Mean($close,3) - Mean($vwap,3) ) )

## Hypothesis

Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 5 ) * Sign( Mean($close,3) - Mean($vwap,3) ) )

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Std(Div(Sub($close, $open), Add($volume, Mul(0.01, Mean($volume, 20)))), 5) * Sign(Sub(Mean($close, 3), Mean($vwap, 3))))```

**Math Formula**: \text{Rank}\left( \text{Std}_{t=1}^{5}\left( \frac{C_t - O_t}{V_t + 0.01\cdot \text{Mean}(V,20)} \right) \cdot \text{Sign}\left( \text{Mean}(C,3) - \text{Mean}(\text{VWAP},3) \right) \right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0870 / 0.0750
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
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
