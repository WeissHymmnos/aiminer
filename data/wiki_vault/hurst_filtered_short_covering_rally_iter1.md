---
title: "Hurst-Filtered Short-Covering Rally"
slug: "hurst_filtered_short_covering_rally_iter1"
type: "factor_card"
status: "failed"
summary: "Go long stocks whose 5-day price Hurst < 0.42 (mean-reverting) AND whose 2-day cumulative short-volume ratio (estimated via intraday tick-rule) jumps from bott…"
updated: "2026-04-14T12:04:08"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Go long stocks whose 5-day price Hurst < 0.42 (mean-reverting) AND whose 2-day cumulative short-volume ratio (estimated via intraday tick-rule) jumps from bottom-quintile to top-quintile while 1-day return is < -1.5%; factor = Rank(Hurst5<0.42) * Rank(Delta(ShortVolumeRatio,2)) * (-Rank(Delta(Close,1))).

**Rationale**: Macro: With the Fed signaling a prolonged pause and U.S. retail sales missing for a third straight month, recession worry is forcing prime-brokers to tighten hedge-fund leverage; the cheapest shorts are crowded low-float tech and small-caps.  Micro: Gu-Kelly shows that when short-interest surges in already anti-persistent names, the subsequent buy-to-cover drives a 1.8% next-day bounce on average; GTJA’s tick-rule proxy isolates short flow without lagged exchange data.  A sub-0.42 Hurst filter avoids the persistent-trend failures seen in prior cards, while the negative return threshold ensures we enter after forced selling, not fundamental drift.

**Implementation (Qlib)**: `If(Less(Ts_Percentile($close,5,50),0.42),CSRank(Delta($volume,2)),0) * -CSRank(Delta($close,1))`

**Math Formula**: Factor = \mathbb{1}_{H_5<0.42}\cdot \text{Rank}\left(\Delta SVR_{2}\right)\cdot \left(-\text{Rank}\left(r_{1}\right)\right)

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor produces flat signals (all zero) because the code tests Ts_Percentile($close,5,50) < 0.42 instead of the intended Hurst exponent; percentile of price is never < 0.42, so the first term is always 0 and the whole expression collapses. IC, Rank-IC, RRE and Sharpe are therefore 0.

**Suggested Improvements**: Replace Ts_Percentile($close,5,50) with a 5-day Hurst exponent estimate (e.g., rescaled range or DMA) and ensure it is compared to 0.42. Use the correct short-volume field (not $volume) and compute its 2-day change in cross-sectional rank. Add sector/neutral ranks, winsorize inputs, and test longer holding horizons to raise IC above 0.02.
