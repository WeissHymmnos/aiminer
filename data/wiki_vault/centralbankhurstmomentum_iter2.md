---
title: "CentralBankHurstMomentum"
slug: "centralbankhurstmomentum_iter2"
type: "experiment_card"
status: "active"
summary: "Hypothesis: During high-volatility bear regimes, rank assets by the product of their 60-day Hurst exponent and the surprise component of th…"
updated: "2026-04-12T14:38:04.579495"
tags: []
related: ["strategy_families_base", "momentum_family", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "volume_divergence_signal"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["momentum_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# CentralBankHurstMomentum

## Summary

Hypothesis: During high-volatility bear regimes, rank assets by the product of their 60-day Hurst exponent and the surprise component of th…

## Hypothesis

Hypothesis: During high-volatility bear regimes, rank assets by the product of their 60-day Hurst exponent and the surprise component of th…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```And(Greater(Std($close,21),Mean(Std($close,21),252)+1*Std(Std($close,21),252)),Less(Delta(Log($close),250),0))```

**Math Formula**: \left\{ i \in \text{universe} \mid \sigma^{(m)}_{t} > \bar{\sigma}_{t}^{(m)} + k \cdot \text{std}_{\tau}(\sigma^{(m)}_{\tau}) \right\} \; \cap \; \left\{ \text{ret}_{t-250:t}^{(m)} < 0 \right\}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `active`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
