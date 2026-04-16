---
title: "Shrinking-Volume Reversal"
slug: "shrinking_volume_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: After two consecutive weeks of below-average volume while price remains above its 20-day MA, next-week CSI-300 return is negati…"
updated: "2026-04-11T20:44:37.400170"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# Shrinking-Volume Reversal

## Summary

Hypothesis: After two consecutive weeks of below-average volume while price remains above its 20-day MA, next-week CSI-300 return is negati…

## Hypothesis

Hypothesis: After two consecutive weeks of below-average volume while price remains above its 20-day MA, next-week CSI-300 return is negati…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Less($volume,Mean(Ref($volume,1),52)),Less($volume,Mean($volume,52)),Greater($close,Mean($close,20))),$close-Ref($close,5),0)```

**Math Formula**: R_{t+1} = \alpha + \beta \, R_t \, I_t + \varepsilon_{t+1}, \quad \beta < 0

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
