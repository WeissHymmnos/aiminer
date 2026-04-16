---
title: "Cross-Sectional Liquidity-Adjusted Policy-Shadow Beta"
slug: "cross_sectional_liquidity_adjusted_policy_shadow_beta_iter3"
type: "experiment_card"
status: "failed"
summary: "Rank( Delta(Close,5) / (StdDev(Volume,20)*Ref(Close,-1)) * Corr(Delta(Close,3),Delta(2YSwapRate,3),30) ) captures stocks whose recent 5-day return per unit of…"
updated: "2026-04-14T12:15:48"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "-0.0066"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cross-Sectional Liquidity-Adjusted Policy-Shadow Beta

## Summary

Rank( Delta(Close,5) / (StdDev(Volume,20)*Ref(Close,-1)) * Corr(Delta(Close,3),Delta(2YSwapRate,3),30) ) captures stocks whose recent 5-day return per unit of…

## Hypothesis

Rank( Delta(Close,5) / (StdDev(Volume,20)*Ref(Close,-1)) * Corr(Delta(Close,3),Delta(2YSwapRate,3),30) ) captures stocks whose recent 5-day return per unit of…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close,5) / (Std($volume,20) * Ref($close,1)) * Corr(Delta($close,3), Delta($close,3), 30))```

**Math Formula**: R_i = \text{rank}_i\left(\frac{\Delta_5 P_i}{\sigma_{20}(V_i)\cdot P_{i,-1}}\cdot \rho_{30}\left(\Delta_3 P_i,\Delta_3 S\right)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** -0.0066 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
