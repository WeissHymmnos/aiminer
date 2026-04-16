---
title: "Liquidity-Adjusted Overnight Gap Reversal with Sector-Neutralization"
slug: "liquidity_adjusted_overnight_gap_reversal_with_sector_neutralization_iter1"
type: "factor_card"
status: "failed"
summary: "Go long on stocks that gapped down overnight (Open/Close-1 < 0) yet simultaneously posted the steepest 3-day volume rank decay within their sector; factor = Se…"
updated: "2026-04-13T20:11:39"
tags: ["利用复杂网络与知识图谱挖掘产业链关联的图计算专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0201
rank_ic: -0.0072
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Go long on stocks that gapped down overnight (Open/Close-1 < 0) yet simultaneously posted the steepest 3-day volume rank decay within their sector; factor = SectorRank(Open/Close-1) * (-SectorRank(Delta(Volume,3))) so the most negative gap and largest volume shrinkage receive highest score.

**Rationale**: With the central bank on hold and volatility compressed, overnight gaps driven by stale sentiment rather than liquidity commitment quickly mean-revert. By sector-neutralizing we remove industry-specific news shocks, isolating microstructure over-reaction: a down gap on evaporating volume signals weak follow-through, prompting next-day bargain hunting. This avoids the double-rank cross-section overlap that killed the intraday version and explicitly conditions reversal on liquidity withdrawal, aligning with Gu-Kelly evidence that volume contraction predicts price reversals.

**Implementation (Qlib)**: `CSRank($open / Ref($close,1) - 1) * (-CSRank(Delta($volume,3)))`

**Math Formula**: \text{Signal}_{i,t}=\text{SectorRank}_{s,t}\left(\frac{O_{i,t}}{C_{i,t-1}}-1\right)\;\times\;\left(-\text{SectorRank}_{s,t}\left(\Delta_{3}\text{Vol}_{i,t}\right)\right)

**IC / RankIC**: -0.0201 / -0.0072

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows negative IC (-0.0201) and Rank IC (-0.0072), both below the 0.02 threshold, indicating weak or inverse predictive power. Sharpe is deeply negative (-2.49) and max drawdown exceeds -63%, suggesting poor risk-adjusted returns. Zero RRE, PFS, and diversity imply no alpha generation, no consistency, and high concentration. The overnight gap-down plus volume-decay signal is not rewarded by the market; instead it appears to select stocks that continue to underperform.

**Suggested Improvements**: 1) Flip the sign: test going long stocks that gap UP overnight with the steepest 3-day volume decay, or short the current factor. 2) Replace raw gap with residual gap adjusted for beta/sector move to isolate idiosyncratic shock. 3) Condition on earnings-announcement or news flags so the gap is information-based, not noise. 4) Replace equal-weighted sector rank with float-adjusted liquidity weight and cap-neutral construction. 5) Add a quality filter (e.g., Z-score of balance-sheet strength) to avoid value-trap losers. 6) Shorten volume decay to 1-day or use turnover ratio vs 20-day avg to capture liquidity contraction more quickly. 7) Apply a market-state overlay: only activate signal when VIX > 25 or market return < -1% to exploit panic selling reversals.
