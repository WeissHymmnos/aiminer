---
title: "Liquidity Shock Reversal"
slug: "liquidity_shock_reversal_iter1"
type: "factor_card"
status: "proven"
summary: "Within the first 30 minutes after a sudden ≥1.5% index gap down on no major headline, fade the 3-minute RSI <25 extreme by buying the most short-term oversold…"
updated: "2026-04-13T19:11:09"
tags: ["You are an expert in mean-reversion trad", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.118
rank_ic: -0.035
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Within the first 30 minutes after a sudden ≥1.5% index gap down on no major headline, fade the 3-minute RSI <25 extreme by buying the most short-term oversold large-cap ETF constituents; exit on first 3-minute RSI >55 or at 15:45 local whichever is earlier.

**Rationale**: In a macro climate of cautious central-bank rhetoric and sticky core inflation, unexplained gap-downs are often liquidity events rather than fundamental repricings. Algo-driven selling triggers stops, pushing prices below fair-value bands; once the order imbalance clears, depth replenishes and mean-reversion is swift. The tight intraday window limits overnight risk while capturing the statistical tendency for noise shocks to reverse within the same session.

**Implementation (Qlib)**: `If(And(LessEqual(0, 0), LessEqual(0, 0), LessEqual(Delta($close, 1) / Ref($close, 1), -0.015), LessEqual(0, 0), Less(Ts_Rank(Mean($close, 3), 3), 25), LessEqual(CSRank($close), 50)), 1, 0)`

**Math Formula**: \text{Entry}_t = \left\{ \begin{array}{ll} 1, & \text{if } t \in [T_0, T_0+30\text{min}] \,\land\, \frac{I_{t_0}-I_{t_0-1}}{I_{t_0-1}} \leq -0.015 \,\land\, \text{Headline}_{t_0}=0 \,\land\, \text{RSI}_{3\text{min}}(t) < 25 \,\land\, \text{CapRank}_i(t) \leq K \\ 0, & \text{otherwise} \end{array} \right. \quad\quad \text{Exit}_t = \min\!\left\{ \inf\!\left\{ t' > t \mid \text{RSI}_{3\text{min}}(t') > 55 \right\},\; 15\!:\!45 \right\)

**IC / RankIC**: 0.1180 / -0.0350

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.118 > 0.02 threshold and excellent PFS1 0.93, but Rank IC is negative (-0.035) indicating rank ordering is inverted versus expectation. RRE 0.30 and diversity 0.28 are acceptable. LLM score 78.5 supports logic coherence. Negative Rank IC suggests the ‘most oversold’ ranking is actually selecting weaker performers; likely the CSRank($close) is ranking by price level instead of RSI or gap-adjusted momentum. Factor is effective but mis-specified ranking needs correction.

**Suggested Improvements**: Replace CSRank($close) with CSRank(Ts_Rank(Mean($close, 3), 3)) or CSRank(RSI(3)) to correctly rank stocks by short-term oversold condition. Add liquidity filter (e.g., $volume > 95th percentile) to ensure large-cap ETF constituents are tradable. Consider tightening entry RSI threshold to <20 and exit RSI to >50 to reduce false positives. Add minimum 5-cent bid-ask spread filter to mitigate micro-structure noise. Test holding until 15:45 vs earlier RSI exit to verify time-decay assumption.
