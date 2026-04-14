---
title: "Liquidity-Adjusted Sector-Relative Reversal on Fed-Pivot Shock"
slug: "liquidity_adjusted_sector_relative_reversal_on_fed_pivot_shock_iter3"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta(Close,5) / Sqrt(Mean(Volume,5)))  If(Rank(Corr(Delta(Close,3),Delta(VIX,1),15))>0.7,-1,1)  Sign(Rank(Delta(Close,5…"
updated: "2026-04-11T20:47:32.478459"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta(Close,5) / Sqrt(Mean(Volume,5))) * If(Rank(Corr(Delta(Close,3),Delta(VIX,1),15))>0.7,-1,1) * Sign(Rank(Delta(Close,5)) - Rank(Delta(Close,5),'sector')) ) goes long (short) stocks whose 5-day price move, scaled by the square-root of recent volume, is extreme only when their 3-day return co-moves strongly with VIX spikes and the move is worse (better) than the 5-day sector median, expecting rapid reversal as the market digests a hawkish Fed pivot and liquidity provision normalizes.
**Rationale**: With the Fed signalling higher-for-longer and cross-asset volatility spiking, crowded low-liquidity selloffs inside each sector create transient dislocations. The square-root volume divisor penalises illiquid names, the VIX correlation flag isolates shock-driven moves, and the sector-relative rank ensures we bet on intra-sector mean reversion rather than macro momentum. This hybrid captures liquidity-aware reversal conditioned on volatility-regime feedback, orthogonal to prior failed pure-price or Fed-futures filters.
**Implementation (Qlib)**: `Rank(Multiply(Divide(Delta($close,5),Sqrt(Mean($volume,5))),If(Greater(CSRank(Corr(Delta($close,3),Delta($vwap,1),15)),0.7),-1,1))) * Sign(Subtract(Rank(Delta($close,5)),CSRank(Delta($close,5))))`
**Math Formula**: \text{Rank}\left( \frac{\Delta(C_t,5)}{\sqrt{\text{Mean}(V_t,5)}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\text{Corr}\left(\Delta(C_t,3),\Delta(\text{VIX}_t,1),15\right)\right)\,>\,0.7\right\}}\cdot(-1) + \frac{\Delta(C_t,5)}{\sqrt{\text{Mean}(V_t,5)}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\text{Corr}\left(\Delta(C_t,3),\Delta(\text{VIX}_t,1),15\right)\right)\,\le\,0.7\right\}}\cdot1 \right) \cdot \text{Sign}\left(\text{Rank}\left(\Delta(C_t,5)\right) - \text{Rank}_{\text{sector}}\left(\Delta(C_t,5)\right)\right)
**IC / RankIC**: 0.0000 / 0.0000
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows zero IC, Rank IC, and all performance metrics, indicating no predictive power or alpha generation. The signal construction may be too complex or the conditions too restrictive, leading to no meaningful signal extraction.
**Suggested Improvements**: Simplify the factor by removing the VIX correlation filter or adjusting its threshold (0.7 is too high), replace vwap with actual VIX data, test shorter or longer deltas, and verify sector-neutralization logic. Consider using z-scores instead of ranks for smoother signals and test on a broader universe to ensure sufficient signal coverage.
