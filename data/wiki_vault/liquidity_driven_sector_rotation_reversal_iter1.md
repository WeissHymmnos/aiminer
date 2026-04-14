---
title: "Liquidity-Driven Sector Rotation Reversal"
slug: "liquidity_driven_sector_rotation_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  Sign(Rank($volume,63) - 0.5)  Sign(Rank($close/Ref($close,21)) - Rank($close/Ref($c…"
updated: "2026-04-11T20:50:07.902792"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta($close,5) / Delta($volume,5)) * Sign(Rank($volume,63) - 0.5) * Sign(Rank($close/Ref($close,21)) - Rank($close/Ref($close,21), 'sector')) ) goes long (short) stocks whose 5-day price move is large vs volume, have below-median 63-day volume rank, and whose 21-day return ranks below sector median, expecting low-liquidity laggards to snap back as sector rotation momentum exhausts.
**Rationale**: With the Fed on hold and macro data softening, sector rotation momentum has become choppy. Low-liquidity names that underperformed their sector over 21 days but experienced a sharp 5-day price/volume spike are often temporary hedges or overcrowded shorts; when sector leadership wavers these illiquid laggards revert fastest. Conditioning on below-median 63-day volume rank isolates names most sensitive to order-flow imbalances, while the sector-relative return rank ensures we pick stocks still out of favor on a cross-sectional basis, avoiding crowded winners. This combines mean-reversion, liquidity dynamics, and sector-neutral positioning to exploit the current high-volatility, no-trend regime.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Delta($close,5),Delta($volume,5)),Sign(Subtract(Rank(Mean($volume,63)),0.5))),Sign(Subtract(Rank(Divide($close,Ref($close,21))),CSRank(Divide($close,Ref($close,21)))))))`
**Math Formula**: R = \text{Rank}\left( \frac{\Delta(C,5)}{\Delta(V,5)} \cdot \text{Sign}\left(\text{Rank}(V,63) - 0.5\right) \cdot \text{Sign}\left(\text{Rank}\left(\frac{C}{C_{21}}\right) - \text{Rank}_{\text{sector}}\left(\frac{C}{C_{21}}\right)\right) \right)
**IC / RankIC**: -0.0008 / 0.0006
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows near-zero IC (-0.0008) and Rank IC (0.0006), negative Sharpe (-0.09), deep max-drawdown (-39%), zero hit-rate metrics, and no sector or style diversity; the combined signal is effectively noise, contradicting the expected mean-reversion in low-liquidity laggards.
**Suggested Improvements**: 1) Replace 5-day Δprice/Δvolume ratio with a normalized liquidity shock (z-score vs 21-day history) to isolate genuine liquidity dislocations. 2) Flip the volume-rank condition: go long stocks with above-median 63-day volume rank (recent liquidity uptake) instead of below-median. 3) Use sector-relative 21-day return decile spread (top vs bottom quintile within sector) rather than simple rank difference to sharpen rotation signal. 4) Add a short-term reversal filter (e.g., 5-day return < -5%) to ensure entry after a pullback. 5) Apply market-neutral sector weighting and cap-scaling to reduce drawdown and raise IC; target IC > 0.02 before live allocation.
