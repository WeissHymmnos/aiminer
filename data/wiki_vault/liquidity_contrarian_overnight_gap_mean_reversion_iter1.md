---
title: "Liquidity-Contrarian Overnight Gap Mean-Reversion"
slug: "liquidity_contrarian_overnight_gap_mean_reversion_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up overnight on sharply shrinking volume tend to mean-revert intraday; factor = -Rank((Open-PrevClose)/PrevClose) * Rank((PrevVolume-Ref(PrevVo…"
updated: "2026-04-13T20:11:34"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0195
rank_ic: -0.0037
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Stocks that gap up overnight on sharply shrinking volume tend to mean-revert intraday; factor = -Rank((Open-PrevClose)/PrevClose) * Rank((PrevVolume-Ref(PrevVolume,5))/Ref(PrevVolume,5)) where higher rank of negative volume change amplifies contrarian signal.

**Rationale**: With the central bank on hold and macro uncertainty elevated, investors react cautiously to overnight news, creating liquidity-starved gaps that lack follow-through. Shrinking 5-day volume rank flags waning participation, while the overnight return rank isolates sentiment-driven extremes; together they capture a low-risk reversal as stale longs exit when volume does not confirm the move.

**Implementation (Qlib)**: `-Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank((Ref($volume,1) - Ref($volume,5)) / Ref($volume,5))`

**Math Formula**: R_{i,t}=\alpha+\beta F_{i,t}+\varepsilon_{i,t}\quad\text{with}\quad F_{i,t}=-\text{Rank}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\text{Rank}\left(\frac{V_{i,t-1}-V_{i,t-6}}{V_{i,t-6}}\right)

**IC / RankIC**: -0.0195 / -0.0037

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor exhibits weak negative IC (-0.0195) and negligible Rank IC (-0.0037), both below 0.02 threshold; Sharpe deeply negative (-2.31) and max drawdown near -60% indicate poor risk-adjusted performance; zero RRE, PFS, and diversity suggest no alpha, no consistency, and no portfolio spread; LLM score 0.0 corroborates failure.

**Suggested Improvements**: 1) Replace raw 5-day volume reference with smoother 5-day average volume to reduce noise; 2) Add sector-neutral ranking to control for sector-specific volume patterns; 3) Introduce overnight gap size filter (e.g., |gap| > 1σ) to isolate extreme mean-reversion candidates; 4) Scale volume change by 20-day median volume to normalize across market caps; 5) Combine with intraday momentum reversal proxy (e.g., first-hour RSI) to sharpen timing; 6) Winsorize inputs at 1-99% to curb outliers; 7) Test decile spreads instead of continuous factor to verify monotonicity.
