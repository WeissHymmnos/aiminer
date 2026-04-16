---
title: "HMM-State-Filtered Liquidity Surge Momentum"
slug: "hmm_state_filtered_liquidity_surge_momentum_iter1"
type: "experiment_card"
status: "active"
summary: "Regime-state probability from a 2-state HMM on overnight gap and first-hour volume predicts next-day return; factor = HMM_state_prob(BullSurge) * Rank(Delta(Vo…"
updated: "2026-04-13T20:11:33"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.034"
rank_ic: "0.013"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# HMM-State-Filtered Liquidity Surge Momentum

## Summary

Regime-state probability from a 2-state HMM on overnight gap and first-hour volume predicts next-day return; factor = HMM_state_prob(BullSurge) * Rank(Delta(Vo…

## Hypothesis

Regime-state probability from a 2-state HMM on overnight gap and first-hour volume predicts next-day return; factor = HMM_state_prob(BullSurge) * Rank(Delta(Vo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater($open - Ref($close,1), 0.5 * Mean(Abs($high - $low), 20)), Ts_Rank($volume, 20) * Rank(Delta($volume, 1)) * Sign(Delta($close, 1)), 0)```

**Math Formula**: r_{t+1}=\mathbb{1}_{g_t>0.5\cdot\text{ATR}_{20}}\cdot\pi_t(\text{BullSurge})\cdot\text{Rank}\left(\Delta V_t\right)\cdot\text{Sign}(\Delta C_t)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0340 / 0.0130
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[implementation_drift_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
