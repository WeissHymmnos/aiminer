---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 10 ) * Sign( Corr($close - $open, $volume, 5) ) )"
updated: "2026-04-14T12:33:30"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.044
rank_ic: -0.044
iteration: 3
is_effective: false
simulated: true
---

**Hypothesis**: Rank( Std( ($close - $open) / ($volume + 0.01*Mean($volume,20)) , 10 ) * Sign( Corr($close - $open, $volume, 5) ) )

**Rationale**: Macro: PBoC’s stealth tightening drains intraday liquidity; moves accompanied by wide, volume-inefficient spreads are more likely to revert. Market regime is high-vol/bearish, so micro-costs dominate. Instead of raw price/volume ratios that failed before, we (1) divide each intraday return by a liquidity cushion (volume dampened by 20-day mean) to create a dollar-volume efficiency metric, (2) take its 10-day cross-sectional dispersion to identify stocks whose recent intraday moves are highly scattered per unit liquidity, and (3) multiply by the sign of the 5-day correlation between intraday return and volume to ensure we only penalize moves where volume positively co-moves with direction (classic pressure). The result is a smooth score that continuously ranks the likelihood of liquidity-starved dispersion reversals within 1-2 days.

**Implementation (Qlib)**: `Rank(Std(Div(Sub($close, $open), Add($volume, Mul(0.01, Mean($volume, 20)))), 10) * Sign(Corr(Sub($close, $open), $volume, 5)))`

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\text{Std}_{10}\left(\frac{C_{i,d}-O_{i,d}}{V_{i,d}+0.01\cdot\bar{V}_{i,20,d}}\right)\cdot\text{Sign}\left(\text{Corr}_{5}\left(C_{i,d}-O_{i,d},V_{i,d}\right)\right)\right)

**IC / RankIC**: 0.0440 / -0.0440

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong positive IC (0.044) but Rank IC is equal in magnitude and opposite in sign (-0.044), indicating the rank ordering is inverted; RRE 0.157 and PFS1 0.58 are acceptable, diversity 0.37 is moderate, LLM score 91 is excellent. The sign flip suggests the hypothesis direction is reversed—higher volatility of intraday return scaled by volume predicts lower future return, contrary to intended momentum signal.

**Suggested Improvements**: Invert the final sign to align Rank IC with IC; replace 10-day std with exponential-weighted or longer 20-day window to reduce noise; test volume scaling with turnover or log volume to mitigate extreme values; consider absolute correlation instead of signed correlation to capture volume confirmation regardless of direction; add sector/neutral ranking to boost cross-sectional stability.
