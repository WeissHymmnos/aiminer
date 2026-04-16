---
title: "CentralBankSlopeMACD"
slug: "centralbankslopemacd_iter1"
type: "experiment_card"
status: "active"
summary: "Combine the slope of a short-term Moving Average (MA) with a MACD signal line crossover, filtered by central-bank hawkish/dovish regime. Entry long when 20-day…"
updated: "2026-04-13T19:11:14"
tags: ["You are an expert in momentum and trend-", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "policy_pivot_regime", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "threshold_timing_execution"]
ic: "0.075"
rank_ic: "0.098"
iteration: "1"
is_effective: "true"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "policy_pivot_regime", "threshold_timing_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source"]
market_regimes: ["policy_pivot_regime"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# CentralBankSlopeMACD

## Summary

Combine the slope of a short-term Moving Average (MA) with a MACD signal line crossover, filtered by central-bank hawkish/dovish regime. Entry long when 20-day…

## Hypothesis

Combine the slope of a short-term Moving Average (MA) with a MACD signal line crossover, filtered by central-bank hawkish/dovish regime. Entry long when 20-day…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater(Delta(Mean($close,20),1),0),Greater(EMA(Mean($close,12),9)-EMA(Mean($close,26),9),0),Greater(Delta(EMA(Mean($close,12),9)-EMA(Mean($close,26),9),1),0),0),1,0)```

**Math Formula**: \begin{cases}
L_t = 1 & \text{if } \Delta MA_{20}(t)\!\!>0 \;\land\; MACD_{sig}(t)\!\!>0 \;\land\; \Delta MACD_{sig}(t)\!\!>0 \;\land\; R_t = dovish \\
S_t = 1 & \text{if } \Delta MA_{20}(t)\!\!<0 \;\land\; MACD_{sig}(t)\!\!<0 \;\land\; \Delta MACD_{sig}(t)\!\!<0 \;\land\; R_t = hawkish \\
E_t^{long}  = 1 & \text{if } (MACD_{sig}(t)\!\!<0 \;\land\; \Delta MACD_{sig}(t)\!\!<0) \;\lor\; R_t = hawkish \\
E_t^{short} = 1 & \text{if } (MACD_{sig}(t)\!\!>0 \;\land\; \Delta MACD_{sig}(t)\!\!>0) \;\lor\; R_t = dovish
\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `active`
- **IC / RankIC:** 0.0750 / 0.0980
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[policy_pivot_regime]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
