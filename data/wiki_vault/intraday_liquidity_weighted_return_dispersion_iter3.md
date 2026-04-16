---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 10 ) * Sign( Corr($close - $open, $volume, 5) ) )"
updated: "2026-04-14T12:33:30"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.044"
rank_ic: "-0.044"
iteration: "3"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Intraday Liquidity-Weighted Return Dispersion

## Summary

Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 10 ) * Sign( Corr($close - $open, $volume, 5) ) )

## Hypothesis

Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 10 ) * Sign( Corr($close - $open, $volume, 5) ) )

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Std(Div(Sub($close, $open), Add($volume, Mul(0.01, Mean($volume, 20)))), 10) * Sign(Corr(Sub($close, $open), $volume, 5)))```

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\text{Std}_{10}\left(\frac{C_{i,d}-O_{i,d}}{V_{i,d}+0.01\cdot\bar{V}_{i,20,d}}\right)\cdot\text{Sign}\left(\text{Corr}_{5}\left(C_{i,d}-O_{i,d},V_{i,d}\right)\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0440 / -0.0440
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[turnover_explosion_risk]]

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
