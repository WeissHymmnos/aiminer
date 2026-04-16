---
title: "Liquidity-Adjusted Sector-Relative Reversal on Fed-Driven Volatility Shock"
slug: "liquidity_adjusted_sector_relative_reversal_on_fed_driven_volatility_shock_iter2"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( (TsArgMin($close,5)==1)  (Rank($volume / TsMean($volume,20))<0.2)  Sign(Rank($close/Ref($close,1)) - Rank($close/Ref($clo…"
updated: "2026-04-11T20:50:26.942270"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime", "policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Adjusted Sector-Relative Reversal on Fed-Driven Volatility Shock

## Summary

Hypothesis: Rank( (TsArgMin($close,5)==1)  (Rank($volume / TsMean($volume,20))<0.2)  Sign(Rank($close/Ref($close,1)) - Rank($close/Ref($clo…

## Hypothesis

Hypothesis: Rank( (TsArgMin($close,5)==1)  (Rank($volume / TsMean($volume,20))<0.2)  Sign(Rank($close/Ref($close,1)) - Rank($close/Ref($clo…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(Equal(Ts_ArgMin($close,5),1),Less(Rank(Div($volume,Mean($volume,20))),0.2)),Sign(Sub(Rank(Div($close,Ref($close,1))),CSRank(Div($close,Ref($close,1))))),0))```

**Math Formula**: R = \text{Rank}\left(\mathbf{1}_{\left\{ \text{Ts_ArgMin}(C_t,5)=1 \right\}} \cdot \mathbf{1}_{\left\{ \text{Rank}\left(\frac{V_t}{\bar{V}_{20}}\right)<0.2 \right\}} \cdot \text{Sign}\left( \text{Rank}\left(\frac{C_t}{C_{t-1}}\right) - \text{Rank}_{\text{sector}}\left(\frac{C_t}{C_{t-1}}\right) \right) \right)

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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
