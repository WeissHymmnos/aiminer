---
title: "Volume-Weighted Intraday Gradient Reversal"
slug: "volume_weighted_intraday_gradient_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5) + 1e-6) * Exp(-Abs(Delta($vwap/$close,1))) ) goes long (short) stocks whose 1-day close change is large relative to the…"
updated: "2026-04-14T12:25:51"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($close,1) / (Std($volume,5) + 1e-6) * Exp(-Abs(Delta($vwap/$close,1))) ) goes long (short) stocks whose 1-day close change is large relative to their own recent volume volatility, but the move stays close to VWAP (small exponent), expecting that volume-amplified yet VWAP-coherent moves quickly exhaust liquidity and mean-revert within 1-2 days.

**Rationale**: Macro: With the Fed on extended pause and sticky inflation, liquidity is rationed; moves that flare on elevated volume but do not break far from VWAP are typically transient order-flow imbalances rather than genuine information. Market regime is high-vol/bearish, so microstructure reversals dominate. Cross-agent lesson: raw price/volume ratios failed because they ignored volume noise; normalizing by rolling volume Std instead of mean keeps units consistent across large/small caps. Exponential damp on VWAP deviation penalizes only marginal moves, letting the factor stay continuous and cross-sectional rather than binary. The net score ranks all stocks smoothly, capturing liquidity-exhaustion reversals without threshold artifacts.

**Implementation (Qlib)**: `Rank(Mul(Div(Delta($close,1),Add(Std($volume,5),0.000001)),Exp(Neg(Abs(Delta(Div($vwap,$close),1)))))))`

**Math Formula**: R_{t} = \text{rank}_{i}\left(\frac{\Delta P_{i,t}}{\sigma_{V_{i},5,t}+10^{-6}}\cdot\exp\left(-\left|\Delta\left(\frac{VWAP_{i,t}}{P_{i,t}}\right)\right|\right)\right)

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: All metrics are exactly zero, indicating the factor has no predictive power; the price-change/volume-volatility ratio multiplied by a VWAP-proximity damping term produces a flat signal across the universe, so the expected 1-2 day mean-reversion is not captured.

**Suggested Improvements**: 1) Replace 1-day close change with a smoothed 2-5 day return to reduce noise, 2) Normalize volume-volatility by cross-sectional median instead of raw std, 3) Use a signed volume-volatility ratio (return * sign(volume surprise)) to preserve direction, 4) Shorten the VWAP proximity window to intraday 30-min buckets and cap the exponent at 0.5 to avoid near-zero weights, 5) Apply sector-neutral z-score and winsorize at 3σ before ranking, 6) Test holding periods of 1, 3, 5 days with decay weights to confirm mean-reversion timing.
