---
title: "Hurst-Filtered Liquidity Exhaustion Reversal"
slug: "hurst_filtered_liquidity_exhaustion_reversal_iter1"
type: "experiment_card"
status: "active"
summary: "Normalize 5-day Hurst exponent (price) and 3-day Hurst exponent (volume) separately; rank the product of (-Rank(HurstPrice,5)) * (-Rank(HurstVolume,3)) to isol…"
updated: "2026-04-13T20:11:30"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.046"
rank_ic: "0.066"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Hurst-Filtered Liquidity Exhaustion Reversal

## Summary

Normalize 5-day Hurst exponent (price) and 3-day Hurst exponent (volume) separately; rank the product of (-Rank(HurstPrice,5)) * (-Rank(HurstVolume,3)) to isol…

## Hypothesis

Normalize 5-day Hurst exponent (price) and 3-day Hurst exponent (volume) separately; rank the product of (-Rank(HurstPrice,5)) * (-Rank(HurstVolume,3)) to isol…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```-Rank(($close-$open)/($high-$low))*Rank(-CSRank($high)*-CSRank($volume))```

**Math Formula**: S = -\operatorname{rank}_{\text{all}}\left(\frac{C-O}{H-L}\right)\cdot\operatorname{rank}_{\text{all}}\left(-\operatorname{rank}_{\text{sect}}(H_{P,5})\cdot-\operatorname{rank}_{\text{sect}}(H_{V,3})\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0460 / 0.0660
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
