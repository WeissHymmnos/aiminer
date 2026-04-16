---
title: "Hurst-Filtered Cross-Sectional Volume-Price Divergence Reversal"
slug: "hurst_filtered_cross_sectional_volume_price_divergence_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,42)∈[0.35,0.65], -1, 0)  Sign(Corr(Rank($close/Ref($close,5)),Rank($volume),10))  (Mean($volume,3)/Mean($…"
updated: "2026-04-11T20:46:58.072774"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( If(Hurst($close,42)∈[0.35,0.65], -1, 0) * Sign(Corr(Rank($close/Ref($close,5)),Rank($volume),10)) * (Mean($volume,3)/Mean($volume,20)-1) ) goes long (short) stocks whose 10-day price-volume correlation is negative (positive) and whose 3-day volume surge is in the top (bottom) quintile, but only when the 42-day Hurst exponent signals moderate mean-reversion (0.35-0.65), expecting that volume-driven moves in lightly persistent markets exhaust and reverse.
**Rationale**: With the Fed signaling prolonged high rates and global trade volumes softening, liquidity is fragmenting and intraday moves are increasingly noise-driven. A moderate Hurst window (42d) captures the current regime where trends are neither ballistic nor fully choppy. By restricting trades to stocks exhibiting cross-sectional volume-price divergence (negative correlation) and a sudden volume spike, we isolate liquidity shocks that are prone to mean-revert once temporary order imbalances dissipate, yielding a short-horizon reversal alpha without relying on the rare ultra-antipersistent filter that previously killed robustness.
**Implementation (Qlib)**: `Rank(If(And(GreaterEqual(Ts_Percentile($close,42,50),0.35),LessEqual(Ts_Percentile($close,42,50),0.65)),1,0)*Sign(Corr(Rank(Delta($close,5)),Rank($volume),10))*(Mean($volume,3)/Mean($volume,20)-1))`
**Math Formula**: R_{t}=\text{Rank}\!\left(\;\mathbf{1}_{\left[0.35,\,0.65\right]}\!\bigl(H_{42}(P)\bigr)\;\cdot\;\text{sgn}\!\left(\text{Corr}\!\left(\;\text{Rank}\!\left(\frac{P_{t}}{P_{t-5}}\right),\;\text{Rank}(V_{t}),\;10\;\right)\right)\;\cdot\;\left(\frac{\bar{V}_{3}}{\bar{V}_{20}}-1\right)\;\right)
**IC / RankIC**: -0.0011 / -0.0014
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows negligible predictive power with IC and Rank IC near zero and negative Sharpe. The Hurst filter appears to be miscalculated (Ts_Percentile instead of Hurst) and the sign flip on price-volume correlation may be inverted, while the volume surge term is too noisy at 3-day horizon.
**Suggested Improvements**: Replace Ts_Percentile with actual Hurst exponent; test Hurst bounds [0.4,0.6] for stronger mean-reversion signal; flip sign so long (short) stocks have positive (negative) price-volume correlation; smooth volume surge to 5-day/20-day ratio; add sector-neutralization and cap-weighted construction; shrink extreme z-scores to reduce turnover.
