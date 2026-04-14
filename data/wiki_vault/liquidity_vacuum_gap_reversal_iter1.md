---
title: "Liquidity Vacuum Gap Reversal"
slug: "liquidity_vacuum_gap_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)+1e-6) * (1-Abs(Corr($vwap,$close,3))) * Sign(Delta($volume,1)) ) goes long (short) stocks that printed an outsized 1-da…"
updated: "2026-04-14T12:08:23"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0042
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($close,1) / (Std($volume,5)+1e-6) * (1-Abs(Corr($vwap,$close,3))) * Sign(Delta($volume,1)) ) goes long (short) stocks that printed an outsized 1-day price change relative to the typical volume volatility while volume actually dropped and the price drifted away from VWAP, expecting the gap to refill as dormant liquidity re-enters.

**Rationale**: Macro: PBoC’s surprise repo rate cut injects selective liquidity, but dealers remain cautious—volume volatility shrinks while price gaps widen on small orders. Market regime is choppy/range-bound; gaps not validated by volume tend to be noise rather than informed moves. Cross-agent lesson: raw volume denominators and long correlations failed; replacing with 5-day volume std captures liquidity vacuum, while (1-|VWAP correlation|) penalizes moves that deviate from fair price. Volume-drop sign ensures we target liquidity-starved gaps most likely to revert when latent orders re-appear.

**Implementation (Qlib)**: `Rank(Delta($close,1) / (Std($volume,5) + 1e-6) * (1 - Abs(Corr($close,$vwap,3))) * Sign(Delta($volume,1)))`

**Math Formula**: R = \text{rank}\left( \frac{\Delta P_{t}}{\sigma_{V,5}+10^{-6}} \cdot \left(1-\left|\rho_{3}(P,VWAP)\right|\right) \cdot \text{sign}\left(\Delta V_{t}\right) \right)

**IC / RankIC**: -0.0042 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows negligible predictive power: IC and Rank IC are essentially zero, Sharpe is strongly negative (-0.70), and drawdown exceeds 24%. The sign of the price-change term flips when volume rises, yet the signal treats both up- and down-volume shocks the same; this mutes any net exposure. The 3-day VWAP-close correlation window is too short to capture durable drift, and dividing by a 5-day volume std makes the term extremely noisy for low-volume names. No risk adjustment or sector neutrality is applied, so performance is dominated by micro-structure noise and cross-sectional volatility rather than alpha.

**Suggested Improvements**: 1) Replace Sign(Delta(volume,1)) with a capped, signed volume surprise (e.g., Sign*Min(Abs(Delta(volume,1)/Std(volume,20)),3)) to retain direction without binary noise. 2) Extend correlation window to 10-20 days and use rank-zscore to mitigate look-ahead bias. 3) Winsorize the price-change numerator at 1-2% to curb outlier influence. 4) Neutralize the raw signal by sector and size, then standardize cross-sectionally before ranking. 5) Add a liquidity filter (median 20-day dollar-volume > $1M) to ensure the gap-refill hypothesis is tradable. 6) Test a symmetric reversal variant: go long (short) the bottom (top) decile to check whether the negative IC is a genuine reversal effect; if IC turns positive, flip the sign of the final rank.
