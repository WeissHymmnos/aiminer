---
title: "Flight-to-Quality Balance-Sheet Momentum"
slug: "flight_to_quality_balance_sheet_momentum_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (CashAndShortTermInvestmentsQ/MarketCap) * (1/Max(0.01,TotalDebtQ/MarketCap)) * Ts_Zscore(ROC(Close,20),60) ) rewards large-caps whose balance sheets car…"
updated: "2026-04-14T12:15:02"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "momentum_family", "stat_arb_family", "price_volume_data_source", "macro_data_source", "sector_data_source", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution", "volume_divergence_signal"]
ic: "0.0014"
rank_ic: "0.0"
iteration: "1"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Flight-to-Quality Balance-Sheet Momentum

## Summary

Rank( (CashAndShortTermInvestmentsQ/MarketCap) * (1/Max(0.01,TotalDebtQ/MarketCap)) * Ts_Zscore(ROC(Close,20),60) ) rewards large-caps whose balance sheets car…

## Hypothesis

Rank( (CashAndShortTermInvestmentsQ/MarketCap) * (1/Max(0.01,TotalDebtQ/MarketCap)) * Ts_Zscore(ROC(Close,20),60) ) rewards large-caps whose balance sheets car…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Multiply(Multiply(Divide($close, $close), Divide(1, Max(0.01, Divide($close, $close)))), CSZScore(Delta($close, 20))))```

**Math Formula**: R_i = \text{rank}_i\left(\frac{C_i}{M_i} \cdot \frac{1}{\max\!\bigl(0.01,\,D_i/M_i\bigr)} \cdot z\bigl(r_{i,20},\,60\bigr)\right)

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0014 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- None recorded

## Related Concepts

- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
