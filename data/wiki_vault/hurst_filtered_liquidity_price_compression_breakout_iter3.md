---
title: "Hurst-Filtered Liquidity-Price Compression Breakout"
slug: "hurst_filtered_liquidity_price_compression_breakout_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Delta($close,1)) * (Mean($high-$low,3)/Mean($high-$low,20)-1) * (Mean($volume,3)/Mean($volume,20)-1) ) goes…"
updated: "2026-04-14T12:09:21"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0044
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Rank( If(Hurst($close,21)∈[0.45,0.7], 1, 0) * Sign(Delta($close,1)) * (Mean($high-$low,3)/Mean($high-$low,20)-1) * (Mean($volume,3)/Mean($volume,20)-1) ) goes long (short) stocks whose 3-day intraday range has compressed vs 20-day baseline yet 3-day volume has expanded vs 20-day baseline, when 21-day Hurst signals mild trend-persistence (0.45-0.7), expecting that liquidity-absorbed compression periods resolve directionally in lightly persistent markets.

**Rationale**: Macro: With the Fed on an extended pause and global trade volumes shrinking, liquidity is patchy; low-range days on rising volume indicate latent pressure. Market Analysis: Regime is high-vol, bear-leaning; previous mean-reversion-only Hurst filters (<0.4) kept hitting whipsaws, while pure trend filters (>0.7) chased exhausted moves. Literature shows compression-breakout alphas (Alpha 054, GTJA-010) work when volume confirms stored energy. By shifting Hurst band to 0.45-0.7 we capture the current quasi-trend environment where compressed ranges resolve directionally rather than instantly reverting, avoiding the failed mean-reversion logic of earlier agents.

**Implementation (Qlib)**: `Rank(If(And(Greater(Mean($high-$low,21),0.45),Less(Mean($high-$low,21),0.7)),Sign(Delta($close,1))*(Mean($high-$low,3)/Mean($high-$low,20)-1)*(Mean($volume,3)/Mean($volume,20)-1),0))`

**Math Formula**: R = \text{rank}\left[ \mathbb{1}_{[0.45,0.7]}\left(H_{21}\right) \cdot \text{sgn}\left(\Delta C_{1}\right) \cdot \left(\frac{\bar{R}_{3}}{\bar{R}_{20}}-1\right) \cdot \left(\frac{\bar{V}_{3}}{\bar{V}_{20}}-1\right) \right]

**IC / RankIC**: -0.0044 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC ≈ –0.004, Rank IC = 0, negative Sharpe and deep draw-down. The Hurst condition is incorrectly calculated on mean range instead of Hurst exponent, nullifying the intended regime filter; combined with sign-of-one-day return, the signal is largely random noise.

**Suggested Improvements**: 1) Replace Mean($high-$low,21) with actual Hurst($close,21). 2) Drop Sign(Delta($close,1)) and instead use next-day return as target to let the factor pick direction. 3) Winsorize all inputs at 1-2% tails. 4) Consider z-scoring compression & expansion terms and interact them multiplicatively only when Hurst∈[0.45,0.7]. 5) Add sector/neutral caps and liquidity screens; test on multiple horizons (5-20d) to raise IC above 0.02.
