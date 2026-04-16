---
title: "Liquidity-Adjusted Intraday Fake-Out Continuation"
slug: "liquidity_adjusted_intraday_fake_out_continuation_iter1"
type: "experiment_card"
status: "failed"
summary: "Stocks that print an intraday shooting-star (high-low range ≥2×20-day ATR, close in bottom 20% of range) yet simultaneously register a 1-day jump in cancelled…"
updated: "2026-04-13T20:11:53"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base", "mean_reversion_family", "momentum_family", "volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "simulation_only_risk", "information_coefficient_metric", "rank_ic_metric", "cross_sectional_long_short_execution"]
ic: "0.042"
rank_ic: "-0.013"
iteration: "1"
is_effective: "false"
simulated: "true"
node_type: "factor_experiment"
evidence_level: "simulated"
canonical: false
parents: ["mean_reversion_family", "momentum_family"]
depends_on: ["volume_divergence_signal", "price_volume_data_source", "macro_data_source", "sector_data_source", "market_regime_base", "cross_sectional_long_short_execution"]
risk_flags: ["simulation_only_risk"]
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
strategy_family: ["mean_reversion_family", "momentum_family"]
data_sources: ["price_volume_data_source", "macro_data_source", "sector_data_source"]
market_regimes: ["market_regime_base"]
execution_patterns: ["cross_sectional_long_short_execution"]
related_experiments: []
---

# Liquidity-Adjusted Intraday Fake-Out Continuation

## Summary

Stocks that print an intraday shooting-star (high-low range ≥2×20-day ATR, close in bottom 20% of range) yet simultaneously register a 1-day jump in cancelled…

## Hypothesis

Stocks that print an intraday shooting-star (high-low range ≥2×20-day ATR, close in bottom 20% of range) yet simultaneously register a 1-day jump in cancelled…

## Economic Rationale

Rationale not yet captured.

## Formula / Implementation

**Implementation (Qlib)**: ```If(Less($close, Plus(0.2*($high-$low), $low)), Mult(CSRank(Div(Minus($high, $low), EMA(Minus($high, $low), 20))), CSRank(Delta($volume, 1))), 0)```

**Math Formula**: Factor=\begin{cases}\text{Rank}\left(\frac{H-L}{\text{ATR}_{20}}\right)\cdot\text{Rank}\left(\Delta\text{CancelAskVol}_{1}\right)&\text{if }C\leq0.2(H-L)+L\\0&\text{otherwise}\end{cases}

## Backtest Evidence

- **Evidence Level:** `simulated`
- **Status:** `failed`
- **IC / RankIC:** 0.0420 / -0.0130
- **Effectiveness:** ✅ effective

## Interpretation

Interpretation pending.

## Failure Modes / Risks

- [[simulation_only_risk]]

## Related Concepts

- [[mean_reversion_family]]
- [[momentum_family]]
- [[price_volume_data_source]]
- [[macro_data_source]]
- [[sector_data_source]]
- [[market_regime_base]]
- [[cross_sectional_long_short_execution]]

## Next Steps

Promote or refine after collecting stronger evidence.
