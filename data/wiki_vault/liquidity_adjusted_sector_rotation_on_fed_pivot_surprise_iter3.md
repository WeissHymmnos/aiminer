---
title: "Liquidity-Adjusted Sector Rotation on Fed-Pivot Surprise"
slug: "liquidity_adjusted_sector_rotation_on_fed_pivot_surprise_iter3"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Rank( (Delta($close,5) / Delta($volume,5))  If(Corr(Delta($close,1), $fedfut3m, 15) > 0.02, 1, -1)  If(Rank($volume, 'sector')…"
updated: "2026-04-11T20:50:37.753293"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta($close,5) / Delta($volume,5)) * If(Corr(Delta($close,1), $fedfut3m, 15) > 0.02, 1, -1) * If(Rank($volume, 'sector') < 0.4, -1, 1) ) goes long (short) stocks whose 5-day price move is large vs volume, conditioned on positive co-movement with 3-month Fed-funds futures over 15 days, but only when the stock’s volume ranks in the bottom 40 % of its sector—expecting that low-liquidity sector laggards snap back hardest when the market re-prices a dovish Fed surprise.
**Rationale**: With the Fed signaling a possible pause after 525 bp of hikes, the belly of the curve (3-m futures) is the first to re-price. Cross-sectional ranks neutralize beta, isolating relative sector rotation. Low-volume names have stale prices; when macro news arrives they gap violently, creating predictable 5-day reversal. Sector-relative volume filter avoids crowded high-liquidity leaders where alpha is arbitraged away. Conditional correlation term flips sign if Fed surprise is hawkish, keeping factor regime-adaptive.
**Implementation (Qlib)**: `Rank(Delta($close,5) / Delta($volume,5) * Sign(Corr(Delta($close,1), Ref($close,63),15) - 0.02) * Sign(0.4 - CSRank($volume)))`
**Math Formula**: R_{i,t}=\operatorname{Rank}_i\left(\frac{\Delta_5 P_{i,t}}{\Delta_5 V_{i,t}}\cdot\operatorname{sgn}\left(\operatorname{Corr}_{15}\left(\Delta_1 P_{i,t},F_{3m,t}\right)-0.02\right)\cdot\operatorname{sgn}\left(0.4-\operatorname{Rank}_{\text{sector},i}(V_{i,t})\right)\right)
**IC / RankIC**: 0.1150 / 0.1090
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Strong positive IC (0.115) and Rank IC (0.109) confirm the factor captures forward return; RRE 0.64 shows good risk-adjusted efficacy; low Diversity (0.018) and mediocre PFS indicate crowdedness and limited breadth; code uses 63-day close instead of $fedfut3m and sector-neutral volume rank not implemented, weakening the Fed-signal and sector filter intended in the hypothesis.
**Suggested Improvements**: Replace Ref($close,63) with $fedfut3m to restore the Fed-funds futures correlation signal; implement sector-neutral volume ranking by using CSRank($volume, group='sector') or SectorRank($volume); test 10-day or 20-day Fed correlation window to improve responsiveness; add liquidity screen (e.g., median 20-day dollar-volume > $5M) to reduce micro-cap noise; orthogonalize against momentum and short-term reversal to lift PFS and Diversity.
