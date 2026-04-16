---
title: "Mean-Reversion Gamma Trap"
slug: "mean_reversion_gamma_trap_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,30)∈[0.4,0.6], -1, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))  TsRank($close-$open,10)  (…"
updated: "2026-04-11T20:50:11.151248"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "implementation_drift_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "cross_sectional_long_short_execution"]
risk_flags: ["implementation_drift_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Mean-Reversion Gamma Trap

## Summary

Hypothesis: Rank( If(Hurst($close,30)∈[0.4,0.6], -1, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))  TsRank($close-$open,10)  (…

## Hypothesis

Hypothesis: Rank( If(Hurst($close,30)∈[0.4,0.6], -1, 0)  Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))  TsRank($close-$open,10)  (…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(If(And(GreaterEqual(CSRank($close),0.4),LessEqual(CSRank($close),0.6)),-1,0)*Sign(Corr(Rank($close/Ref($close,1)),Rank($volume),5))*Ts_Rank($close-$open,10)*(Std($volume,3)/Std($volume,20)-1))```

**Math Formula**: R = \text{rank}\left(\; \mathbf{1}_{[0.4,0.6]}\!\big(H_{30}(C)\big)\,\cdot\,(-1)\;\cdot\; \text{sign}\!\Big(\text{corr}\!\big(\text{rank}(C_t/C_{t-1}),\;\text{rank}(V_t),\;5\big)\Big)\;\cdot\; \text{TSrank}(C-O,\;10)\;\cdot\;\Big(\frac{\sigma(V,3)}{\sigma(V,20)}-1\Big)\;\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ❌ not validated

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[implementation_drift_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
