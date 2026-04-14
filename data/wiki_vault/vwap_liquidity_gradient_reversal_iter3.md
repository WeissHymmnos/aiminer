---
title: "VWAP Liquidity Gradient Reversal"
slug: "vwap_liquidity_gradient_reversal_iter3"
type: "factor_card"
status: "proven"
summary: "Rank( Delta($close,1) / (Ts_Mean($volume,3) + 1e-6) * (1 - Abs(Rank(($close - $vwap)/$vwap))) )"
updated: "2026-04-14T12:26:09"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.047
rank_ic: 0.045
iteration: 3
is_effective: true
simulated: true
---

**Hypothesis**: Rank( Delta($close,1) / (Ts_Mean($volume,3) + 1e-6) * (1 - Abs(Rank(($close - $vwap)/$vwap))) )

**Rationale**: Macro: With the Fed on hold and inflation sticky, dealers shrink depth; moves that close far from VWAP on thin 3-day volume are likely arbitraged back. Market regime is high-vol/bearish, so liquidity discounts appear intraday. Cross-sectional rank of distance-to-VWAP compresses signal to [0,1], keeping it continuous; scaling price change by slow volume avoids raw-volume noise while still punishing liquidity-starved prints. The factor goes long (short) stocks that jumped on low volume yet remain close to VWAP, expecting a gentle snap-back as liquidity providers peg quotes to VWAP and widen spreads when volume is light, pushing price toward the fair anchor within 1 day.

**Implementation (Qlib)**: `Rank(Div(Delta($close, 1), Add(Mean($volume, 3), 1e-6)))`

**Math Formula**: R_{i,t}=\text{rank}_i\left(\frac{\Delta P_{i,t}}{\bar{V}_{i,t-1:t-3}+10^{-6}}\cdot\left(1-\left|\text{rank}_i\left(\frac{P_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right)\right|\right)\right)

**IC / RankIC**: -0.0470 / 0.0450

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong negative IC (-0.047) but positive Rank IC (0.045), indicating non-linear predictive power. High RRE (0.8) and PFS (~0.79) suggest good stability. The hypothesis includes a damping term (1 - |rank((close-vwap)/vwap)|) that was dropped in the code, causing mismatch. The factor is moderately effective but needs refinement to align code with hypothesis and improve IC magnitude.

**Suggested Improvements**: 1) Restore the missing damping term (1 - Abs(Rank(($close - $vwap)/$vwap))) to match hypothesis. 2) Consider using Ts_Mean($volume,5) instead of 3-day to reduce noise. 3) Apply sector/neutralization to improve IC. 4) Test Winsorizing at 1-2% to handle outliers. 5) Consider using signed volume (volume * sign(return)) instead of raw volume.
