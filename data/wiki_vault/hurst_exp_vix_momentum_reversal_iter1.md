---
title: "Hurst_Exp_VIX_Momentum_Reversal"
slug: "hurst_exp_vix_momentum_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Hypothesis: In high-volatility bear-regimes, long-period Hurst exponent estimates (>250-day lookback) on equity index prices become anti-pe…"
updated: "2026-04-12T14:37:45.984444"
tags: []
related: ["strategy_families_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "information_coefficient_metric", "rank_ic_metric", "threshold_timing_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "vwap_anchor_signal", "hurst_filter_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "high_volatility_regime", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["high_volatility_regime"]
execution_patterns: ["threshold_timing_execution"]
related_experiments: []
---

# Hurst_Exp_VIX_Momentum_Reversal

## Summary

Hypothesis: In high-volatility bear-regimes, long-period Hurst exponent estimates (>250-day lookback) on equity index prices become anti-pe…

## Hypothesis

Hypothesis: In high-volatility bear-regimes, long-period Hurst exponent estimates (>250-day lookback) on equity index prices become anti-pe…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(Greater($vwap, 25), Less(Ts_Percentile($close, 252, 50), 0.45)), If(Less(Delta($close, 5), Ts_Percentile(Delta($close, 5), 50, 10)), 1, If(Greater(Delta($close, 5), Ts_Percentile(Delta($close, 5), 50, 90)), -1, 0)) * Delta(Ref($close, 5), -5), 0)```

**Math Formula**: \alpha_{t} = \frac{1}{N_{t}} \sum_{i=1}^{N_{t}} \left[ \mathbb{1}_{w_{i,t}=+1} \cdot r_{i,t+1:t+5} - \mathbb{1}_{w_{i,t}=-1} \cdot r_{i,t+1:t+5} \right] \quad \text{with} \quad w_{i,t}=+1 \; \text{if} \; R_{i,t-4:t}\leq F_{0.1}\left\{R_{j,t-4:t}\right\}_{j\in\text{SPX}}, \; w_{i,t}=-1 \; \text{if} \; R_{i,t-4:t}\geq F_{0.9}\left\{R_{j,t-4:t}\right\}_{j\in\text{SPX}}, \; \text{subject to} \; VIX_{t}^{\text{close}}>25, \; H_{t}(252)<0.45, \; \text{and} \; \text{exit at} \; t+5 \; \text{or} \; VIX_{\tau}^{\text{close}}<20 \; (\tau\in[t+1,t+5])

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
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[high_volatility_regime]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
