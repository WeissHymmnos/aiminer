---
title: "Order-Flow Imbalance Micro-Trend Exhaustion"
slug: "order_flow_imbalance_micro_trend_exhaustion_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks showing extreme positive order-flow imbalance (Sign(Close-Open)*Volume) over the last 3 days but whose latest 30-minute closing strength (Close-Low)/(Hi…"
updated: "2026-04-13T20:11:39"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "stat_arb_family", "volume_divergence_signal", "price_volume_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "-0.025"
rank_ic: "0.095"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family", "stat_arb_family"]
data_sources: ["price_volume_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Order-Flow Imbalance Micro-Trend Exhaustion

## Summary

Stocks showing extreme positive order-flow imbalance (Sign(Close-Open)*Volume) over the last 3 days but whose latest 30-minute closing strength (Close-Low)/(Hi…

## Hypothesis

Stocks showing extreme positive order-flow imbalance (Sign(Close-Open)*Volume) over the last 3 days but whose latest 30-minute closing strength (Close-Low)/(Hi…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```Rank(Sign($close - $open) * $volume) / Rank(Sign(Ref($close, 1) - Ref($open, 1)) * Ref($volume, 1) + Sign(Ref($close, 2) - Ref($open, 2)) * Ref($volume, 2)) * (-Rank(($close - $low) / ($high - $low) - Mean(($close - $low) / ($high - $low), 5)))```

**Math Formula**: F_{t}=\frac{\text{rank}\left(\text{sign}(C_{t}-O_{t})\cdot V_{t}\right)}{\text{rank}\left(\text{sign}(C_{t-1}-O_{t-1})\cdot V_{t-1}+\text{sign}(C_{t-2}-O_{t-2})\cdot V_{t-2}\right)}\cdot\left(-\text{rank}\left(\frac{C_{t}^{\text{30m}}-L_{t}^{\text{30m}}}{H_{t}^{\text{30m}}-L_{t}^{\text{30m}}}-\frac{1}{5}\sum_{i=0}^{4}\frac{C_{t-i}^{\text{30m}}-L_{t-i}^{\text{30m}}}{H_{t-i}^{\text{30m}}-L_{t-i}^{\text{30m}}}\right)\right)

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** -0.0250 / 0.0950
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[stat_arb_family]]
- [[price_volume_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
