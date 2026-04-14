---
title: "Volume-VWAP Divergence Reversal"
slug: "volume_vwap_divergence_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Go long stocks whose intraday close is below VWAP but where the rolling 5-day correlation between ranked volume and ranked (Clo…"
updated: "2026-04-13T13:52:07.246519"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Go long stocks whose intraday close is below VWAP but where the rolling 5-day correlation between ranked volume and ranked (Close/VWAP-1) has just turned positive; go short the opposite.  Factor = -Rank(Corr(Rank(Volume), Rank((Close-VWAP)/VWAP), 5)) * Sign(Close-VWAP)
**Rationale**: In a cautious-policy, strong-momentum regime volume expansion increasingly validates price moves.  When a stock closes below VWAP yet the high-freq volume/price-dislocation correlation flips positive, it signals latent buy-pressure ready to close the gap, yielding short-term reversal alpha while staying aligned with the prevailing up-trend.
**Implementation (Qlib)**: `-Rank(Corr(CSRank($volume), CSRank(($close - $vwap) / $vwap), 5)) * Sign($close - $vwap)`
**Math Formula**: \text{Factor}_{t} = -\text{Rank}_{\text{all } i}\left(\text{Corr}_{\tau=t-4}^{t}\left(\text{Rank}(V_{i,\tau}),\;\text{Rank}\left(\frac{C_{i,\tau}-\text{VWAP}_{i,\tau}}{\text{VWAP}_{i,\tau}}\right)\right)\right)\;\cdot\;\text{Sign}(C_{i,t}-\text{VWAP}_{i,t})
**IC / RankIC**: 0.0780 / 0.0170
**Effectiveness**: ❌ FAILED
**Review Summary**: Strong directional IC (0.078) but very weak Rank IC (0.017) indicates the factor sorts poorly; long/short baskets overlap. RRE 0.27 and PFS2 0.52 show modest consistency. Diversity 0.83 is healthy. Factor is capturing a linear effect that does not translate into clean quintile spreads, likely because the 5-day correlation window is too noisy and the sign flip is too frequent.
**Suggested Improvements**: Lengthen correlation window to 10-20 days to reduce noise; smooth correlation with exponential decay or z-score before taking sign; replace raw sign(Close-VWAP) with a percentile rank of intraday distance to VWAP so extreme deviations get higher weight; try separate long/short factors (long only when correlation turns from <-0.2 to >0.2 and price < VWAP bottom quintile, short opposite) to restore monotonicity; add liquidity filter (dollar-volume >20-day median) to ensure tradability.
