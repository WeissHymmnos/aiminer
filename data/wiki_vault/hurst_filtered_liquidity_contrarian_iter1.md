---
title: "Hurst-Filtered Liquidity Contrarian"
slug: "hurst_filtered_liquidity_contrarian_iter1"
type: "experiment_card"
status: "failed"
summary: "Go long stocks whose 5-day Hurst exponent < 0.4 (mean-reverting regime) AND whose latest daily volume ranks in the top-quintile but intraday closing strength (…"
updated: "2026-04-13T20:11:39"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "-0.0067"
rank_ic: "0.0173"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Liquidity Contrarian

## Summary

Go long stocks whose 5-day Hurst exponent < 0.4 (mean-reverting regime) AND whose latest daily volume ranks in the top-quintile but intraday closing strength (…

## Hypothesis

Go long stocks whose 5-day Hurst exponent < 0.4 (mean-reverting regime) AND whose latest daily volume ranks in the top-quintile but intraday closing strength (…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less(Ts_Rank($close,5),0.4),CSRank(($close-$low)/($high-$low))*CSRank($volume),0)```

**Math Formula**: \text{Signal}_i = \mathbb{1}_{H_{i,5}<0.4} \cdot \left(-Q_{CloseStrength,i}\right) \cdot Q_{Volume,i}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0067 / 0.0173
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
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
