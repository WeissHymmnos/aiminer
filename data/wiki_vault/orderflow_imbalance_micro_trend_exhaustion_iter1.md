---
title: "OrderFlow Imbalance Micro-Trend Exhaustion"
slug: "orderflow_imbalance_micro_trend_exhaustion_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks whose bid/ask order-flow imbalance (OFI) exceeds +2σ in the first 30 min of trading but whose second-half volume share (13:00-close)/Σday is below its 2…"
updated: "2026-04-13T20:11:53"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.018
rank_ic: 0.122
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks whose bid/ask order-flow imbalance (OFI) exceeds +2σ in the first 30 min of trading but whose second-half volume share (13:00-close)/Σday is below its 20-day median reverse next day; factor = -Zscore(OFI_30min) * Zscore(VolShare_2ndHalf) when both Z>0, else 0.

**Rationale**: With the central bank on hold and macro uncertainty elevated, intraday momentum is increasingly liquidity-constrained. A morning surge of aggressive buy orders (high OFI) that is not validated by sustained afternoon participation (low relative volume) signals stale long positioning and imminent exhaustion. The cross-sectional double-Zscore isolates the most crowded micro-trends while remaining dollar-neutral, capturing the next-day unwind as dealers flatten inventory and algorithms withdraw liquidity.

**Implementation (Qlib)**: `If(And(Greater(CSZScore($volume), 0), Greater(CSZScore($volume), 0)), -CSZScore($volume) * CSZScore($volume), 0)`

**Math Formula**: R_{i,t+1}=\begin{cases}-Z_{\text{OFI},i,t}\cdot Z_{\text{Vol},i,t}&\text{if }Z_{\text{OFI},i,t}>0\text{ and }Z_{\text{Vol},i,t}>0\\0&\text{otherwise}\end{cases}

**IC / RankIC**: -0.0180 / 0.1220

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power: IC is negative and below 0.02 threshold, Rank IC is modestly positive, RRE near 0.5 indicates no edge, PFS1 barely above 5% and PFS2 <50% show poor consistency, diversity is low (0.14), and the code incorrectly uses volume instead of OFI and second-half volume share, making it misaligned with the hypothesis.

**Suggested Improvements**: Fix code to use actual OFI_30min and VolShare_2ndHalf variables; ensure Z-scores are computed on proper lookback windows; consider relaxing the dual-positive-Z condition to capture more signal; test alternative weightings (e.g., rank-based or signed-power) to strengthen IC magnitude; increase holding period or sector-neutralize to raise diversity and RRE.
