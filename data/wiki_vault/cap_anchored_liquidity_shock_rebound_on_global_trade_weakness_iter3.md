---
title: "Cap-Anchored Liquidity Shock Rebound on Global Trade Weakness"
slug: "cap_anchored_liquidity_shock_rebound_on_global_trade_weakness_iter3"
type: "experiment_card"
status: "failed"
summary: "Go long (short) stocks that have underperformed (outperformed) their sector by >3% over the last 10 days while simultaneously experiencing a 20-day low in doll…"
updated: "2026-04-14T12:09:25"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "turnover_explosion_risk", "information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference", "cross_sectional_long_short_execution", "threshold_timing_execution"]
ic: "0.0"
rank_ic: "0.0"
iteration: "3"
is_effective: "false"
simulated: "false"
node_type: "factor_experiment"
evidence_level: "theory"
canonical: false
parents: ["stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution", "threshold_timing_execution"]
risk_flags: ["turnover_explosion_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric", "strategy_risk_metrics_reference"]
strategy_family: ["stat_arb_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution", "threshold_timing_execution"]
related_experiments: []
---

# Cap-Anchored Liquidity Shock Rebound on Global Trade Weakness

## Summary

Go long (short) stocks that have underperformed (outperformed) their sector by >3% over the last 10 days while simultaneously experiencing a 20-day low in doll…

## Hypothesis

Go long (short) stocks that have underperformed (outperformed) their sector by >3% over the last 10 days while simultaneously experiencing a 20-day low in doll…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(And(CSRank($close*$volume)>=0.6667,$volume==Ref($volume,19-Ts_ArgMin($volume,19))),Sign(-(Sum($close/Ref($close,10)-1,10)/Sum($close/Ref($close,10)-1,10)-1)-0.03),0)```

**Math Formula**: w_{i,t}=\mathbb{1}_{\text{top-tercile}(\text{Mcap}_{i,t})}\cdot\text{sign}\left(-\left(\frac{r_{i,t-10:t}}{r_{\text{sector}(i),t-10:t}}-1\right)-0.03\right)\cdot\mathbb{1}_{\left\{DVol_{i,t}=\min_{\tau\in[t-19,t]}DVol_{i,\tau}\right\}}

## Backtest Evidence

- **Evidence Level:** `theory`
- **Status:** `failed`
- **IC / RankIC:** 0.0000 / 0.0000
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[turnover_explosion_risk]]

## Related Concepts

- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]
- [[threshold_timing_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
