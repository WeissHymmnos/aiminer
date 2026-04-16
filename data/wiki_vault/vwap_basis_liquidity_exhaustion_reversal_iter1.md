---
title: "VWAP-Basis Liquidity Exhaustion Reversal"
slug: "vwap_basis_liquidity_exhaustion_reversal_iter1"
type: "experiment_card"
status: "active"
summary: "Next-day reversal signal built from the deviation of close from volume-weighted average price (VWAP) amplified by the rate of liquidity decay: Factor = Rank((C…"
updated: "2026-04-13T20:11:24"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.043"
rank_ic: "0.01"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# VWAP-Basis Liquidity Exhaustion Reversal

## Summary

Next-day reversal signal built from the deviation of close from volume-weighted average price (VWAP) amplified by the rate of liquidity decay: Factor = Rank((C…

## Hypothesis

Next-day reversal signal built from the deviation of close from volume-weighted average price (VWAP) amplified by the rate of liquidity decay: Factor = Rank((C…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Delta($close, $vwap) / $vwap) * (-Rank(Delta($volume, 5)))```

**Math Formula**: F_{i,t}=\text{Rank}_{i}\left(\frac{C_{i,t}-V_{i,t}}{V_{i,t}}\right)\cdot\left(-\text{Rank}_{i}\left(\Delta_{5}Q_{i,t}\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0430 / 0.0100
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
