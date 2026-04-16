---
title: "Hurst-Filtered Liquidity Contrarian"
slug: "hurst_filtered_liquidity_contrarian_iter1"
type: "factor_card"
status: "failed"
summary: "Go long stocks whose 5-day Hurst exponent < 0.4 (mean-reverting regime) AND whose latest daily volume ranks in the top-quintile but intraday closing strength (…"
updated: "2026-04-13T20:11:39"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0067
rank_ic: 0.0173
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Go long stocks whose 5-day Hurst exponent < 0.4 (mean-reverting regime) AND whose latest daily volume ranks in the top-quintile but intraday closing strength (Close-Low)/(High-Low) ranks in the bottom-quintile; factor = Rank(Hurst5<0.4) * (-Rank(CloseStrength)) * Rank(Volume).

**Rationale**: With the central bank on hold and macro uncertainty elevated, the market is stuck in a low-vol, range-bound state; within this backdrop only micro-time-frame mean-reverting names offer reliable alpha. Gu-Kelly shows liquidity spikes in already mean-reverting stocks precipitate sharp reversals as impatient buyers exhaust. GTJA’s closing-strength proxy identifies intraday selling pressure, while a sub-0.4 Hurst filter ensures we trade genuine anti-persistent motion, avoiding the failed double-rank interaction of the prior factor and instead using Hurst as a regime gate to concentrate bets where reversals are statistically expected.

**Implementation (Qlib)**: `If(Less(Ts_Rank($close,5),0.4),CSRank(($close-$low)/($high-$low))*CSRank($volume),0)`

**Math Formula**: \text{Signal}_i = \mathbb{1}_{H_{i,5}<0.4} \cdot \left(-Q_{CloseStrength,i}\right) \cdot Q_{Volume,i}

**IC / RankIC**: -0.0067 / 0.0173

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC is negative and below 0.02, Rank IC is only 0.0173, Sharpe is strongly negative (-1.69), max drawdown exceeds -63%, and all robustness metrics (RRE, PFS, Diversity, LLM) are zero. The triple-rank construction collapses signal-to-noise and the Hurst filter appears mis-specified (Ts_Rank vs exponent estimate).

**Suggested Improvements**: 1) Replace Ts_Rank($close,5) with a true 5-day Hurst exponent estimate (e.g., rescaled range or DMA). 2) Use z-scores or percentile ranks instead of nested CRanks to preserve monotonicity. 3) Test separate layers: first validate Hurst<0.4 universe actually mean-reverts (IC>0.02), then add volume & close-strength filters; consider interaction terms or ML non-linear combo. 4) Shrink extreme weights and impose sector/neutral caps to raise Diversity above 0.5. 5) Extend look-back to 20-60 days to raise signal stability and re-check IC decay; target IC>0.02 and Sharpe>1 before live use.
