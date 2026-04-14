---
title: "Overnight Gap Reversal with Liquidity Surge Filter"
slug: "overnight_gap_reversal_with_liquidity_surge_filter_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5% Open/PrevClose) but experience a same-day surge in lit-depth (top-decile Δ(VisibleBidVolume,1)) tend to mean-revert intrada…"
updated: "2026-04-13T20:11:35"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.016
rank_ic: 0.034
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that gap up overnight (>1.5% Open/PrevClose) but experience a same-day surge in lit-depth (top-decile Δ(VisibleBidVolume,1)) tend to mean-revert intraday; factor = -Rank((Open/Ref(Close,1)-1)) * Rank(Δ(VisibleBidVolume,1)) * Rank(High-Open) when gap>1.5% else 0.

**Rationale**: With the central bank on hold and volatility compressed, overnight gaps often reflect retail FOMO rather than fundamental news; the sudden appearance of deep visible bids signals institutional supply absorbing the retail buying, creating a reliable intraday fade. GTJA shows (High-Open) captures residual buying exhaustion, while Gu-Kelly proves liquidity spikes combined with price extremes forecast reversal. Limiting activation to >1.5% gaps avoids noise and concentrates bets on crowded retail moves.

**Implementation (Qlib)**: `If(Greater(Delta($open,1)/Ref($close,1),0.015),-Rank(Delta($open,1)/Ref($close,1))*Rank(Delta($volume,1))*Rank($high-$open),0)`

**Math Formula**: F_{t}=\begin{cases}-\text{Rank}\left(\frac{O_{t}}{C_{t-1}}-1\right)\cdot\text{Rank}\left(\Delta V_{t}^{\text{lit}}\right)\cdot\text{Rank}\left(H_{t}-O_{t}\right),&\text{if }\frac{O_{t}}{C_{t-1}}-1>0.015\\0,&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0160 / 0.0340

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.016 is below 0.02 threshold; Rank IC 0.034 is modest. RRE 0.063 and PFS1 0.77 show weak directional consistency. Diversity 0.026 indicates low cross-sectional dispersion. LLM score 91.18 suggests good code quality but metrics do not support efficacy.

**Suggested Improvements**: Tighten gap filter to >2% and use percentile-based lit-depth surge (>95th) to sharpen signal. Replace High-Open with (Close-Open)/Open to capture actual intraday reversal. Add sector-neutral rank to reduce noise. Consider intraday half-life decay weighting for faster mean-reversion capture.
