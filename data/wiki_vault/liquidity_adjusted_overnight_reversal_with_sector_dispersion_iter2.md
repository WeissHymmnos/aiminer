---
title: "Liquidity-Adjusted Overnight Reversal with Sector Dispersion"
slug: "liquidity_adjusted_overnight_reversal_with_sector_dispersion_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1) - Ref($open,1)) / Ref($close,2)  Sign(0.2 - Rank($volume / Ref($volume,1)))  Sign(Rank($close / Ref($close…"
updated: "2026-04-11T20:50:22.763378"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Liquidity-Adjusted Overnight Reversal with Sector Dispersion

## Summary

Hypothesis: Rank( (Ref($close,1) - Ref($open,1)) / Ref($close,2)  Sign(0.2 - Rank($volume / Ref($volume,1)))  Sign(Rank($close / Ref($close…

## Hypothesis

Hypothesis: Rank( (Ref($close,1) - Ref($open,1)) / Ref($close,2)  Sign(0.2 - Rank($volume / Ref($volume,1)))  Sign(Rank($close / Ref($close…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide(Minus(Ref($close,1),Ref($open,1)),Ref($close,2)),Sign(Minus(0.2,Rank(Divide($volume,Ref($volume,1)))))),Sign(Minus(CSRank(Divide($close,Ref($close,1))),Rank(Divide($close,Ref($close,1)))))))```

**Math Formula**: \text{Signal}_{t} = \text{Rank}\left( \frac{\text{Ref}(C_{t},1) - \text{Ref}(O_{t},1)}{\text{Ref}(C_{t},2)} \cdot \text{Sign}\left(0.2 - \text{Rank}\left(\frac{V_{t}}{\text{Ref}(V_{t},1)}\right)\right) \cdot \text{Sign}\left(\text{Rank}\left(\frac{C_{t}}{\text{Ref}(C_{t},1)},\text{sector}\right) - \text{Rank}\left(\frac{C_{t}}{\text{Ref}(C_{t},1)}\right)\right) \right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[mean_reversion_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
