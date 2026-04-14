---
title: "Cross-Sectional Hurst-Term Structure Volatility Reversal"
slug: "cross_sectional_hurst_term_structure_volatility_reversal_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( (1 - Hurst($close,18)) * Sign(Delta($close,1)) * (Delta($vwap,1)/$close) * (Std($close,5)/Std($close,30)) ) goes long (short) stocks whose 1-day return i…"
updated: "2026-04-14T12:33:31"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.006
rank_ic: -0.013
iteration: 3
is_effective: false
simulated: true
---

**Hypothesis**: Rank( (1 - Hurst($close,18)) * Sign(Delta($close,1)) * (Delta($vwap,1)/$close) * (Std($close,5)/Std($close,30)) ) goes long (short) stocks whose 1-day return is negative (positive), whose 1-day VWAP move is disproportionately large versus the close, whose 5-day volatility is elevated relative to 30-day volatility, and whose 18-day Hurst exponent is low (<0.5), expecting that intraday mean-reversion is strongest when short-term volatility spikes, term-structure is inverted, and price series show low persistence.

**Rationale**: Macro: May CPI holds sticky at 3.4 %, prompting Fed speakers to re-anchor rate-cut bets for 2025, while flash PMIs show services barely expanding—growth is stalling but inflation is not. Market Analysis: VIX futures now upward-sloping (contango) but 1-week IV >28 %, intraday SPY range 2.1 %, and cross-sector correlation >0.62—regime is high-vol with choppy micro-structure. Low 18-day Hurst (<0.5) isolates names reverting intraday; term-structure volatility spike (5d/30d) flags short-term panic; VWAP-close divergence captures liquidity dislocation. Together they produce a smooth cross-sectional rank that shorts overstretched up-moves and buys oversold down-moves before the next macro headline.

**Implementation (Qlib)**: `Rank(Mul(Sub(1, Ts_Rank($close, 18)), Mul(Sign(Delta($close, 1)), Mul(Div(Delta($vwap, 1), $close), Div(Std($close, 5), Std($close, 30))))))`

**Math Formula**: R_i = \text{rank}_i\left(\left(1 - H_i\right)\cdot\text{sign}\left(r_i\right)\cdot\frac{\Delta v_i}{c_i}\cdot\frac{\sigma_{i,5}}{\sigma_{i,30}}\right)

**IC / RankIC**: -0.0060 / -0.0130

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC and Rank IC are both negative and far below the 0.02 threshold, indicating no predictive power; RRE 0.3 is modest, PFS near 0.5 shows no consistent direction, and low diversity suggests overcrowding. The construction mixes mean-reversion and momentum signals that appear to cancel out, and the Hurst proxy is mis-scaled.

**Suggested Improvements**: Flip the sign on the Hurst term to reward high persistence instead of low; replace Sign(Delta(close,1)) with a smoothed z-score of overnight return; normalize the volatility ratio by its cross-sectional z-score and cap at ±3; lag the VWAP term by one extra day to avoid look-ahead; finally, winsorize all inputs at 1% and neutralize sector/size before ranking.
