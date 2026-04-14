---
title: "Hurst-Volatility-Adjusted Volume Climax Reversal"
slug: "hurst_volatility_adjusted_volume_climax_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Go long stocks whose 5-day price Hurst < 0.45 (mean-reverting) AND whose 3-day realized volatility ranks in the top-decile while 1-day volume delta ranks in th…"
updated: "2026-04-14T12:01:05"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0043
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Go long stocks whose 5-day price Hurst < 0.45 (mean-reverting) AND whose 3-day realized volatility ranks in the top-decile while 1-day volume delta ranks in the top-decile but 1-day return is negative; factor = Rank(Hurst5<0.45) * (-Rank(Delta(Close,1))) * Rank(Delta(Volume,1)) * Rank(RealizedVol3).

**Rationale**: Macro: PBoC’s stealth tightening via daily repo drain keeps CNH rates elevated, forcing leveraged hedge funds to de-risk; high-vol names are cheapest to short so volume spikes on down days flag forced selling rather than fundamental flow. Micro: Gu-Kelly shows that when realized vol is extreme but Hurst indicates anti-persistence the next-day bounce averages 1.2% if volume surge is contra-side; GTJA confirms negative same-day return on vol-volume climax cuts out the failed “buy euphoria” trap that killed prior cards. Combining Hurst filter with vol rank orthogonalizes single-volume persistence failure and exploits current bear-vol regime.

**Implementation (Qlib)**: `If(Less(Ts_Rank($close,5),0.45),Mult(Mult(Neg(Rank(Delta($close,1)/Ref($close,1))),Rank(Delta($volume,1)/Ref($volume,1))),Rank(Std(Delta($close,1)/Ref($close,1),3))),0)`

**Math Formula**: Factor_{i,t}=\mathbb{1}_{H_{i,t}^{(5)}<0.45}\cdot\left(-\text{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-1}}-1\right)\right)\cdot\text{Rank}_{t}\left(\frac{V_{i,t}}{V_{i,t-1}}-1\right)\cdot\text{Rank}_{t}\left(\sigma_{i,t}^{(3)}\right)

**IC / RankIC**: -0.0043 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC is negative (-0.0043) and far below the 0.02 threshold; Rank IC is exactly 0, indicating no monotonic predictive power. Sharpe is negative and drawdown exceeds 25%. The combined filter is too restrictive and the interaction term cancels signal.

**Suggested Improvements**: Replace hard 0.45 Hurst cutoff with a z-score or percentile rank; flip sign on (-Rank(Delta(Close,1))) to reward positive same-day reversal; test volatility and volume decile filters separately to avoid multicollinearity; add sector/neutralization and liquidity screen; shorten look-back to 3-day Hurst and 2-day volatility to raise signal density; verify code matches intent—current implementation zeros factor when Hurst condition fails, shrinking universe excessively.
