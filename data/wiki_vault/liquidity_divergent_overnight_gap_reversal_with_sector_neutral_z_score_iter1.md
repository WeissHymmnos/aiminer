---
title: "Liquidity-Divergent Overnight Gap Reversal with Sector-Neutral Z-Score"
slug: "liquidity_divergent_overnight_gap_reversal_with_sector_neutral_z_score_iter1"
type: "experiment_card"
status: "failed"
summary: "Among stocks that open with a positive gap ≥0.5%, those whose overnight gap rank rises while their 1-day turnover rank simultaneously falls (indicating liquidi…"
updated: "2026-04-13T20:11:59"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "threshold_timing_execution"]
ic: "-0.029"
rank_ic: "0.105"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Divergent Overnight Gap Reversal with Sector-Neutral Z-Score

## Summary

Among stocks that open with a positive gap ≥0.5%, those whose overnight gap rank rises while their 1-day turnover rank simultaneously falls (indicating liquidi…

## Hypothesis

Among stocks that open with a positive gap ≥0.5%, those whose overnight gap rank rises while their 1-day turnover rank simultaneously falls (indicating liquidi…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(($open - Ref($close,1)) / Ref($close,1), 0.005), CSZScore(($open - Ref($close,1)) / Ref($close,1)) * (-CSZScore(Delta($volume,1) / Ref($volume,1))), 0)```

**Math Formula**: F_{i,t}=\begin{cases}Z_{\text{OG},s}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\left(-Z_{\text{TO},s}\left(\frac{T_{i,t}-T_{i,t-1}}{T_{i,t-1}}\right)\right)&\text{if }\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\geq 0.005\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0290 / 0.1050
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
- [[market_regime_base]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
