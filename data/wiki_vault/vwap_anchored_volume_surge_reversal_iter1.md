---
title: "VWAP-Anchored Volume-Surge Reversal"
slug: "vwap_anchored_volume_surge_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that close well above their volume-weighted average price (VWAP) on a day when volume spikes to a 20-day high but intraday range shrinks tend to mean-re…"
updated: "2026-04-13T20:11:25"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.006
rank_ic: 0.01
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that close well above their volume-weighted average price (VWAP) on a day when volume spikes to a 20-day high but intraday range shrinks tend to mean-revert next day. Factor = Rank((Close-VWAP)/VWAP) * Rank(volume/ts_max(volume,20)) * (-Rank((High-Low)/Ref((High-Low),1)))

**Rationale**: With the central bank on hold and macro uncertainty elevated, liquidity-driven bursts that compress intraday range while pushing price above VWAP are unsustainable; the volume spike signals temporary order-flow imbalance rather than durable trend, so the tight range combined with VWAP premium flags intraday exhaustion ripe for next-day reversal. Cross-sectional ranking neutralizes broad drift and lets the factor isolate microstructure frictions without repeating the prior double-rank structure that muted signal.

**Implementation (Qlib)**: `CSRank(Delta($close,0)/$vwap)*CSRank($volume/Ts_Percentile($volume,20,100))*(-CSRank(Delta($high-$low,0)/Ref($high-$low,1)))`

**Math Formula**: Factor_{i,t}=\text{Rank}_t\left(\frac{\text{Close}_{i,t}-\text{VWAP}_{i,t}}{\text{VWAP}_{i,t}}\right)\cdot\text{Rank}_t\left(\frac{\text{Volume}_{i,t}}{\max_{k=1..20}\text{Volume}_{i,t-k}}\right)\cdot\left(-\text{Rank}_t\left(\frac{\text{High}_{i,t}-\text{Low}_{i,t}}{\text{High}_{i,t-1}-\text{Low}_{i,t-1}}\right)\right)

**IC / RankIC**: 0.0060 / 0.0100

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.006 and Rank IC 0.01 are far below the 0.02 threshold, indicating negligible predictive power; RRE 0.31 and high PFS show the signal is already crowded; diversity 0.73 is acceptable but the LLM score 56 is mediocre. The triple-rank construction dilutes the mean-reversion message and the (-rank) flip on contracting range may be offsetting rather than amplifying the reversal effect.

**Suggested Improvements**: 1) Replace triple-rank interaction with a simple z-score composite to preserve directional magnitude. 2) Demand a minimum 1.5 σ close-to-VWAP gap and a 20-day volume breakout (ratio > 2) before scoring. 3) Use next-day open-to-close return instead of close-to-close to capture the intended overnight mean-reversion. 4) Add sector-neutralization and liquidity filter (top 80% ADV) to reduce micro-cap noise. 5) Shrink extreme tails with winsorization at 1% and 99% to lower turnover and improve IC.
