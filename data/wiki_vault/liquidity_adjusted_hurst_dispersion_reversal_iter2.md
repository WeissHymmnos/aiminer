---
title: "Liquidity-Adjusted Hurst Dispersion Reversal"
slug: "liquidity_adjusted_hurst_dispersion_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,20)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (Std($close,5)/Mean($close,20)) * (1-Abs(Corr(Delta($close,1),Delta(…"
updated: "2026-04-14T12:33:09"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.001
rank_ic: 0.136
iteration: 2
is_effective: false
simulated: true
---

**Hypothesis**: Rank( (1-Hurst($close,20)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (Std($close,5)/Mean($close,20)) * (1-Abs(Corr(Delta($close,1),Delta($volume,1),15))) ) goes long (short) stocks whose 1-day return is negative (positive), whose 1-day volume change is large vs 20-day mean, whose 5-day price volatility is elevated vs 20-day mean, whose 15-day price-volume correlation is low in absolute terms, and whose 20-day Hurst is low (<0.5), expecting that liquidity-driven one-day reversals are strongest when persistence is weakest, volatility is stretched, and volume surprises are not accompanied by coherent price moves.

**Rationale**: Macro: May CPI printed 3.2 % vs 3.0 % expected, keeping Fed dot-plot biased toward one more hike in Q3; global PMI new-export-orders sub-index at 47.3, its sixth consecutive sub-50 read—liquidity is draining while goods trade stalls. Market Analysis: VIX 24 %, SPY 10-day realized vol 19 %, intraday range 2.1 %; cross-sectional dispersion (90th-10th daily return) at 4.8 %, highest since Mar-23—single-stock noise is elevated. In this high-vol, low-liquidity regime, ephemeral volume bursts push prices away from short-term fair value, but low Hurst (<0.5) signals that such moves are not sustainable. By scaling the reversal signal with contemporaneous volatility dispersion and requiring low absolute price-volume correlation, we isolate liquidity shocks that are likely to mean-revert quickly, producing a smooth cross-sectional ranking rather than a binary flag.

**Implementation (Qlib)**: `Rank(Mul(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 20)), Sign(Delta(Log($close), 1))), Div(Delta($volume, 1), Mean($volume, 20))), Div(Std($close, 5), Mean($close, 20))), Sub(1, Abs(Corr(Delta(Log($close), 1), Delta(Log($volume), 1), 15)))))`

**Math Formula**: R_{i,t}=\text{rank}_t\left(\left(1-H_{i,t}^{(20)}\right)\cdot\text{sign}\left(r_{i,t}^{(1)}\right)\cdot\frac{\Delta V_{i,t}^{(1)}}{\bar{V}_{i,t}^{(20)}}\cdot\frac{\sigma_{i,t}^{(5)}}{\bar{P}_{i,t}^{(20)}}\cdot\left(1-\left|\rho_{i,t}^{(15)}\right|\right)\right)

**IC / RankIC**: -0.0010 / 0.1360

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power: IC near zero and negative, while Rank IC of 0.136 is modest but below 0.15 threshold. High RRE (0.965) and Diversity (0.964) indicate good robustness and low overlap with existing factors. PFS metrics suggest reasonable but not strong portfolio formation. LLM score of 74.3 indicates decent complexity. The negative IC contradicts the long-short expectation, suggesting the factor may be inverted or the construction has issues.

**Suggested Improvements**: 1) Remove the Sign(Delta($close,1)) term as it creates a forced inverse relationship that may conflict with other components 2) Consider using absolute or squared values for volume change to capture magnitude rather than direction 3) Replace Hurst exponent with a simpler mean reversion indicator like RSI or z-score 4) Add sector/neutralization to reduce systematic bias 5) Test different time windows (10,30,60 days) for volatility and correlation measures 6) Consider capping extreme values to reduce noise impact 7) Add a market cap filter to focus on liquid stocks where volume surprises matter more
