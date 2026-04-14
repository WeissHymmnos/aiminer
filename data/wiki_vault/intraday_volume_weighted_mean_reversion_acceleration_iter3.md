---
title: "Intraday Volume-Weighted Mean Reversion Acceleration"
slug: "intraday_volume_weighted_mean_reversion_acceleration_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)+1e-6) * Sign(Corr($vwap,$close,3)) * (1-Abs(Corr($close,$volume,3))) ) goes long stocks whose 1-day price change is lar…"
updated: "2026-04-14T12:15:47"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0044
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($close,1) / (Std($volume,5)+1e-6) * Sign(Corr($vwap,$close,3)) * (1-Abs(Corr($close,$volume,3))) ) goes long stocks whose 1-day price change is large relative to recent volume noise, whose price is diverging from VWAP, and whose price-volume correlation is weakening, expecting that liquidity-starved acceleration away from fair value snaps back faster when volume confirmation disappears.

**Rationale**: Macro: PBoC maintains tight liquidity bias while export data surprises to the downside; micro-structure theory says quote adjustments accelerate when volume fails to validate price extension. Market regime is high-vol/bear-leaning; intraday reversals dominate as risk-off algos pull quotes. Cross-agent lesson: raw price/volume ratios flatten signal; scaling price change by volume noise and multiplying by (1-|corr|) keeps signal continuous and penalizes stocks where volume still tracks price, avoiding prior failures that assigned equal scores to crowded moves.

**Implementation (Qlib)**: `Rank(Delta($close,1) / (Std($volume,5) + 0.000001) * Sign(Corr($vwap,$close,3)) * (1 - Abs(Corr($close,$volume,3))))`

**Math Formula**: \text{Signal}_i = \text{Rank}\left( \frac{\Delta P_{i,1}}{\sigma_{V_i,5}+10^{-6}} \cdot \text{Sign}\left(\rho_{i}^{(PV,3)}\right) \cdot \left(1 - \left|\rho_{i}^{(CP,3)}\right|\right) \right)

**IC / RankIC**: 0.0044 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: IC of 0.0044 and Rank IC of 0.0 are far below the 0.02 threshold, indicating the factor has no predictive power; Sharpe of 1.05 is driven by portfolio construction rather than alpha. The signal is drowned out by excessive normalization and interaction terms that cancel opposing effects.

**Suggested Improvements**: Replace Rank with z-score; shrink denominator to Std($volume,5) clipped at 5th/95th pctile instead of adding 1e-6; isolate momentum component by splitting into two factors: (1) Delta($close,1)/Std($volume,5) and (2) Sign(Corr($vwap,$close,3))*(1-Abs(Corr($close,$volume,3))), then combine with a weighted sum or ML model; extend look-back to 10-20 days to reduce noise; neutralize sector/size exposures before ranking; test exponential smoothing on volume noise estimate.
