---
title: "Liquidity-Adjusted Sector-Relative Reversal"
slug: "liquidity_adjusted_sector_relative_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,1)  (1/Rank($volume))  Sign(Rank($close/Ref($close,5)) - Rank($close/Ref($close,5),'sect…"
updated: "2026-04-11T20:47:14.257694"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ref($close,1)-$open)/Ref($close,1) * (1/Rank($volume)) * Sign(Rank($close/Ref($close,5)) - Rank($close/Ref($close,5),'sector')) ) goes short (long) stocks whose overnight gap is large, liquidity rank is low, and 5-day return is weak vs sector, expecting 1-day mean-reversion as under-owned laggards catch up when volume normalizes.
**Rationale**: With the Fed on hold and implied vol elevated, overnight gaps in low-volume, sector-lagging names are often liquidity gaps rather than information. Once intraday liquidity returns, these gaps historically close as risk-parity desks rebalance toward cheap beta inside each sector, making the reversal both fast and uncrowded.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),-1),Ref($close,1)),Divide(1,Rank($volume))),Sign(Minus(Rank(Divide($close,Ref($close,5))),CSRank(Divide($close,Ref($close,5)))))))`
**Math Formula**: R = \text{Rank}\left(\frac{\text{Ref}(C,1)-O}{\text{Ref}(C,1)} \cdot \frac{1}{\text{Rank}(V)} \cdot \text{Sign}\left(\text{Rank}\left(\frac{C}{\text{Ref}(C,5)}\right) - \text{Rank}\left(\frac{C}{\text{Ref}(C,5)},\text{sector}\right)\right)\right)
**IC / RankIC**: 0.0022 / 0.0007
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor IC 0.0022 and Rank IC 0.0007 are far below 0.02 threshold; negative Sharpe and deep draw-down indicate the signal is not capturing 1-day mean-reversion. Zero RRE, PFS and diversity show the alpha is flat and crowded. The triple interaction overdilutes any residual reversion and the sign-of-sector-rank difference adds noise without material edge.
**Suggested Improvements**: Strip the sign term and sector-relative rank; instead use a simple overnight gap decile interacted with a standardized volume z-score, then apply a short-term reversal tail filter (e.g., bottom 20 % 5-day return). Shrink universe to high-volume stocks to avoid liquidity artifacts, and smooth the signal with a 2-day exponential decay to raise IC above 0.02 while controlling turnover.
