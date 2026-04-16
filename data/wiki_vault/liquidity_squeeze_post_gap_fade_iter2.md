---
title: "Liquidity-Squeeze Post-Gap Fade"
slug: "liquidity_squeeze_post_gap_fade_iter2"
type: "experiment_card"
status: "active"
summary: "Stocks that gap up >1% on the open but immediately show a 1-day surge in hidden liquidity cost (measured as % of volume executed at bid/ask midpoint instead of…"
updated: "2026-04-13T20:11:56"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "simulation_only_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution"]
ic: "0.143"
rank_ic: "0.035"
iteration: "2"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "policy_pivot_regime", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Squeeze Post-Gap Fade

## Summary

Stocks that gap up >1% on the open but immediately show a 1-day surge in hidden liquidity cost (measured as % of volume executed at bid/ask midpoint instead of…

## Hypothesis

Stocks that gap up >1% on the open but immediately show a 1-day surge in hidden liquidity cost (measured as % of volume executed at bid/ask midpoint instead of…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Greater(($open - Ref($close,1)) / Ref($close,1), 0.01), -Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank(Delta($volume / $volume,1)), 0)```

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_{c}\left(\frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}\right)\cdot\text{Rank}_{c}\left(\Delta\left(\frac{V^{\text{mid}}_{i,t}}{V_{i,t}},1\right)\right)&\text{if }\frac{\text{Open}_{i,t}-\text{Close}_{i,t-1}}{\text{Close}_{i,t-1}}>0.01\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.1430 / 0.0350
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
- [[policy_pivot_regime]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
