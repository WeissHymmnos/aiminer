---
title: "Disinflation-Divergence Momentum"
slug: "disinflation_divergence_momentum_iter1"
type: "experiment_card"
status: "failed"
summary: "Go long the equal-weight quintile of CSI-300 stocks whose 21-day EMA is above the 63-day EMA, MACD-line > signal-line, and whose latest CPI-sector beta (estima…"
updated: "2026-04-13T19:11:14"
tags: ["You are an expert in momentum and trend-", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "volume_divergence_signal"]
ic: "-0.04"
rank_ic: "0.031"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk", "implementation_drift_risk", "turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Disinflation-Divergence Momentum

## Summary

Go long the equal-weight quintile of CSI-300 stocks whose 21-day EMA is above the 63-day EMA, MACD-line > signal-line, and whose latest CPI-sector beta (estima…

## Hypothesis

Go long the equal-weight quintile of CSI-300 stocks whose 21-day EMA is above the 63-day EMA, MACD-line > signal-line, and whose latest CPI-sector beta (estima…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(EMA($close,21),EMA($close,63)),Greater(Delta(EMA($close,12),EMA($close,26)),EMA(Delta(EMA($close,12),EMA($close,26)),9))),If(Less(CSRank(Delta(CSRank($close),252)),0.2),$close,0),0) - If(And(Greater(EMA($close,21),EMA($close,63)),Greater(Delta(EMA($close,12),EMA($close,26)),EMA(Delta(EMA($close,12),EMA($close,26)),9))),If(Greater(CSRank(Delta(CSRank($close),252)),0.8),$close,0),0)```

**Math Formula**: R_t = \frac{1}{|L_t|}\sum_{i\in L_t}r_{i,t} - \frac{1}{|S_t|}\sum_{j\in S_t}r_{j,t}
\quad\text{with}\quad
L_t = \left\{i\in\text{CSI300}:\;\text{EMA}_{21}(P_{i,t})>\text{EMA}_{63}(P_{i,t}),\;\text{MACD}_{i,t}>\text{Signal}_{i,t},\;i\in Q_{1,t}^{\beta}\right\}
\quad\text{and}\quad
S_t = \left\{j\in\text{CSI300}:\;\text{EMA}_{21}(P_{j,t})>\text{EMA}_{63}(P_{j,t}),\;\text{MACD}_{j,t}>\text{Signal}_{j,t},\;j\in Q_{5,t}^{\beta}\right\}
\quad\text{where}\quad
Q_{1,t}^{\beta} = \arg\min_{\mathcal{Q}\subset\text{CSI300},|\mathcal{Q}|=60}\Delta\beta_{i,t}^{\text{CPI}},
\quad
Q_{5,t}^{\beta} = \arg\max_{\mathcal{Q}\subset\text{CSI300},|\mathcal{Q}|=60}\Delta\beta_{i,t}^{\text{CPI}}
\quad\text{and}\quad
\Delta\beta_{i,t}^{\text{CPI}} = \beta_{i,t}^{\text{CPI}} - \beta_{i,t-252}^{\text{CPI}}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0400 / 0.0310
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]
- [[implementation_drift_risk]]
- [[turnover_explosion_risk]]

## Related Concepts

- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
