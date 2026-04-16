---
title: "Cross-Sectional Gamma-Squeeze Reversal with Gamma-Adjusted Volume"
slug: "cross_sectional_gamma_squeeze_reversal_with_gamma_adjusted_volume_iter1"
type: "factor_card"
status: "failed"
summary: "Rank stocks by how much their 1-day return is stretched relative to the contemporaneous change in 0DTE option gamma, scaled by the deviation of volume from its…"
updated: "2026-04-14T12:26:00"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.006
rank_ic: -0.02
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Rank stocks by how much their 1-day return is stretched relative to the contemporaneous change in 0DTE option gamma, scaled by the deviation of volume from its 10-day low. Go long the most negative residuals (oversold on gamma-expansion) and short the most positive residuals (overbought on gamma-contraction).

**Rationale**: With the SEC’s April 28 approval of same-day expiry options on S&P-500 constituents, 0DTE gamma now dominates intraday flow. When dealers are short gamma they hedge by buying intraday rallies and selling dips, amplifying moves; when gamma flips long the effect reverses. After a gamma-spike day, stocks whose prices rose most while gamma swung from short to long are artificially bid up and tend to revert within 3 days as the gamma wall decays. Conversely, stocks that fell on a gamma-expansion (dealers short-cover) are transiently cheap. Ranking the residual of price change regressed on gamma change, then scaling by distance from 10-day volume trough, isolates the pure gamma-squeeze distortion from fundamental flow, producing a smooth cross-sectional reversal signal that is strongest in the current high-vol, low-conviction regime.

**Implementation (Qlib)**: `CSRank(Neg(Sub(Log(Div($close,Ref($close,1))),Add(GroupNeutral(Log(Div($close,Ref($close,1)))),Mul(GroupNeutral(Delta($volume,1)),Div(Corr(Log(Div($close,Ref($close,1))),Delta($volume,1),20),Std(Delta($volume,1),20))))))))`

**Math Formula**: R_{i,t}=\frac{r_{i,t}}{\Delta\Gamma_{i,t}\,/\,(V_{i,t}-\min_{k=1..10}V_{i,t-k})}\quad\text{with}\quad\text{signal}=\text{rank}(-\hat{\varepsilon}_{i,t})\;\text{for long},\;\text{rank}(+\hat{\varepsilon}_{i,t})\;\text{for short},\;\text{where}\;r_{i,t}=\ln(P_{i,t}/P_{i,t-1}),\;\Delta\Gamma_{i,t}=\Gamma_{i,t}^{0DTE}-\Gamma_{i,t-1}^{0DTE},\;\hat{\varepsilon}_{i,t}=r_{i,t}-\hat{\alpha}-\hat{\beta}\Delta\Gamma_{i,t}

**IC / RankIC**: 0.0060 / -0.0200

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power: IC 0.006 < 0.02 threshold and negative Rank IC contradict long/short premise. High RRE (0.245) and mediocre PFS indicate unstable returns. Diversity 0.17 suggests overlap with existing factors. LLM score 78.63 implies reasonable construction but metrics override this.

**Suggested Improvements**: 1) Replace 0DTE gamma proxy with actual gamma exposure data or 1-day ATM gamma change 2) Use rank-based residual method instead of regression to reduce noise 3) Add sector/market cap neutralization to isolate gamma effect 4) Increase lookback to 60 days for volume deviation baseline 5) Test inverse signal: long positive residuals when gamma contracts (short covering) 6) Add volatility regime filter - only trade when VIX > 20 for stronger gamma effects
