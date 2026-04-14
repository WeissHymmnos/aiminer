---
title: "Liquidity-Adjusted Intraday Fake-Out Continuation"
slug: "liquidity_adjusted_intraday_fake_out_continuation_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that print an intraday shooting-star (high-low range ≥2×20-day ATR, close in bottom 20% of range) yet simultaneously register a 1-day jump in cancelled…"
updated: "2026-04-13T20:11:53"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.042
rank_ic: -0.013
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that print an intraday shooting-star (high-low range ≥2×20-day ATR, close in bottom 20% of range) yet simultaneously register a 1-day jump in cancelled ask volume rank are more likely to trend in the same direction the next morning; factor = Rank((high-low)/ATR20) * Rank(Delta(CancelAskVol,1)) when Close≤0.2×(High-Low)+Low, else 0.

**Rationale**: With the central bank on prolonged hold, dealers provide tight liquidity during low-vol ranges; a wide intraday range that closes on its lows accompanied by a spike in cancelled offers signals aggressive short covering rather than genuine selling. This fake-out exhausts nearby liquidity pockets, leaving fewer resting orders to cap the following session’s continuation move. Unlike the prior double-rank reversal attempt, this construction aligns volume cancellation with price structure to capture liquidity vacuum continuation instead of reversal.

**Implementation (Qlib)**: `If(Less($close, Plus(0.2*($high-$low), $low)), Mult(CSRank(Div(Minus($high, $low), EMA(Minus($high, $low), 20))), CSRank(Delta($volume, 1))), 0)`

**Math Formula**: Factor=\begin{cases}\text{Rank}\left(\frac{H-L}{\text{ATR}_{20}}\right)\cdot\text{Rank}\left(\Delta\text{CancelAskVol}_{1}\right)&\text{if }C\leq0.2(H-L)+L\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0420 / -0.0130

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong positive IC (0.042) but negative Rank IC (-0.013), indicating the linear signal works but rank ordering is poor; RRE 0.163 and PFS1 0.089 are acceptable, yet PFS2 0.624 is weak; high diversity (0.752) suggests low overlap with common factors. The code mistakenly uses Delta($volume,1) instead of cancelled-ask volume, invalidating the hypothesis.

**Suggested Improvements**: Replace Delta($volume,1) with Delta($cancel_ask_vol,1) to align with hypothesis; consider flipping the sign of the second rank term or using a difference-of-ranks to fix negative Rank IC; tighten shooting-star filter by requiring upper wick ≥70% of range and lower wick ≤10%; neutralize sector/size exposures before ranking; test intraday half-life decay by predicting 30-minute instead of next-day returns.
