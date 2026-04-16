---
title: "Overnight Gap Reversal with Liquidity Confirmation"
slug: "overnight_gap_reversal_with_liquidity_confirmation_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank versus their 5-day average reverse next-day; factor = -Rank(GapUp…"
updated: "2026-04-13T20:11:23"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.005
rank_ic: -0.013
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank versus their 5-day average reverse next-day; factor = -Rank(GapUp) * Rank(Delta(DollarVolume,5)) where GapUp=(Open-PrevClose)/PrevClose and DollarVolume=$close*$volume. Only applied to stocks whose intraday amplitude (High-Low)/Open < 2% to isolate low-volatility grind conditions.

**Rationale**: With the central bank on hold and implied vol compressed, overnight gaps on thin volume reflect knee-jerk reactions rather than sustained conviction. GTJA shows gaps >1% revert when not validated by volume, while Gu-Kelly confirms liquidity contraction predicts reversals. Cross-sectional ranking neutralizes the flat market drift, letting the factor capture microstructure exhaustion in a low-vol regime.

**Implementation (Qlib)**: `-1 * Rank(($open - Ref($close,1)) / Ref($close,1)) * Rank(Delta($close * $volume,5)) * Greater(($open - Ref($close,1)) / Ref($close,1), 0.015) * Less(($high - $low) / $open, 0.02)`

**Math Formula**: F_{i,t}= -\text{Rank}_t\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\text{Rank}_t\left(\Delta\left(C_{i,t}\cdot V_{i,t},5\right)\right)\cdot\mathbf{1}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}>0.015\right)\cdot\mathbf{1}\left(\frac{H_{i,t}-L_{i,t}}{O_{i,t}}<0.02\right)

**IC / RankIC**: 0.0050 / -0.0130

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.005 is far below 0.02 threshold; Rank IC -0.013 is weak and opposite to hypothesized reversal. PFS1 0.54 shows slight long-side edge but PFS2 0.26 indicates poor short-side, so signal is not capturing the intended reversal. RRE 0.22 and Diversity 0.80 are acceptable, yet low predictive power dominates. Likely causes: (1) raw 5-day Δ$volume too noisy, (2) hard 1.5 % gap filter removes too many names, (3) low-vol filter (<2 % amplitude) may coincide with stocks that already mean-revert intraday, leaving no overnight edge, (4) rank interaction dilutes signal because both legs can be extreme independently.

**Suggested Improvements**: Replace Δ$volume with Δturnover-ratio or Δvolume-volatility to reduce size bias; shrink gap filter to 0.8–1 % and use smooth z-score instead of rank; interact only when volume shrinkage is in bottom decile; add overnight volume/auction imbalance to confirm lack of follow-through; test separate low-vol vs normal-vol regimes instead of hard filter; try residual gap (vs sector or ETF) to remove market-wide bounce effect; consider short-horizon mean-reversion alpha as a baseline and verify this factor adds orthogonal IC beyond it.
