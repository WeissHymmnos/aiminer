---
title: "Liquidity-Triggered Overnight Gap Reversal"
slug: "liquidity_triggered_overnight_gap_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that open with a positive gap >0.5% but show a sudden 1-day surge in cancelled order volume (proxy for cancelled buy-orders) reverse intraday; factor =…"
updated: "2026-04-13T20:11:20"
tags: ["利用复杂网络与知识图谱挖掘产业链关联的图计算专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.007
rank_ic: 0.066
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that open with a positive gap >0.5% but show a sudden 1-day surge in cancelled order volume (proxy for cancelled buy-orders) reverse intraday; factor = Rank(OpenGap) * Rank(Delta(CancelVolume,1)) * -1 when OpenGap>0.5%, else 0.

**Rationale**: With the central bank on hold and volatility compressed, algorithms crowd into the same overnight momentum trades; a visible gap accompanied by a spike in cancelled volume signals failed aggressive buyers and imminent liquidity withdrawal, leading to intraday mean-reversion as stale longs are unwound.

**Implementation (Qlib)**: `If(Greater(Delta($open, $close), 0.005), -Rank(Delta($open, $close)) * Rank(Delta($volume, 1)), 0)`

**Math Formula**: f_t = \begin{cases}-\mathrm{rank}(\mathrm{OpenGap}_t)\cdot\mathrm{rank}(\Delta\mathrm{CancelVolume}_t) & \text{if }\mathrm{OpenGap}_t>0.005\\ 0 & \text{otherwise}\end{cases}

**IC / RankIC**: 0.0070 / 0.0660

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power with IC 0.007 < 0.02 threshold; Rank IC 0.066 is moderate but inconsistent with low IC; high RRE 0.981 and PFS1 0.899 suggest overfitting; diversity 0.037 indicates low uniqueness; LLM score 89.24 is high but not supported by metrics

**Suggested Improvements**: 1) Fix code mismatch: implement actual cancelled buy-order volume instead of total volume 2) Add volume surge threshold (e.g., >2σ) to filter noise 3) Replace rank product with z-score standardization 4) Add intraday momentum filter (e.g., RSI(14) < 70) 5) Test alternative gap thresholds (0.3%, 0.7%) 6) Add sector neutrality constraint 7) Reduce lookback period for volume delta to avoid data snooping
