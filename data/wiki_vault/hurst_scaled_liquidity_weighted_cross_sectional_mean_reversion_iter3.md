---
title: "Hurst-Scaled Liquidity-Weighted Cross-Sectional Mean-Reversion"
slug: "hurst_scaled_liquidity_weighted_cross_sectional_mean_reversion_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,24)) * Rank(Delta($close,1)) * (1-Corr(Rank($volume),Rank($close),7)) * ($volume/Mean($volume,20)-1) ) goes long the stocks with the most…"
updated: "2026-04-14T12:16:21"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0014
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1-Hurst($close,24)) * Rank(Delta($close,1)) * (1-Corr(Rank($volume),Rank($close),7)) * ($volume/Mean($volume,20)-1) ) goes long the stocks with the most negative 1-day return, lowest 7-day price-volume rank correlation, and highest volume spike relative to 20-day mean, scaled by low 24-day Hurst (<0.5), expecting that liquidity-driven reversals are strongest when persistence is weakest and volume confirms the move.

**Rationale**: Macro: May CPI surprised to the upside (3.5 % vs 3.4 %), pushing Fed fund futures to price only one 25 bp cut in 2024; liquidity is draining as overnight repo prints 5.35 %. Market Analysis: 20-day realized vol for SPY >22 % and intraday range averaging 1.9 % indicate a choppy, mean-reverting regime. Prior failures show binary Hurst gates and volume-only spikes are noisy; instead we use (1-Hurst) as a continuous scaler, rank-weight price move, and interact volume confirmation through a cross-sectional correlation term to isolate reversals that are both liquidity-anchored and persistence-penalized.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Multiply(Sub(1, Ts_Rank($close, 24)), Rank(Delta($close, 1))), Sub(1, Corr(Rank($volume), Rank($close), 7))), Sub(Div($volume, Mean($volume, 20)), 1)))`

**Math Formula**: R_{i,t}=\operatorname{Rank}_t\left(\left[1-H_{i,t}(24)\right]\cdot\operatorname{Rank}_t\left(\Delta C_{i,t}(1)\right)\cdot\left[1-\rho_{i,t}\left(\operatorname{Rank}_t(V_{i,t}),\operatorname{Rank}_t(C_{i,t}),7\right)\right]\cdot\left(\frac{V_{i,t}}{\bar{V}_{i,t}(20)}-1\right)\right)

**IC / RankIC**: -0.0014 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC≈0, Rank IC=0, negative Sharpe (-0.48) and deep drawdown (-60%) contradict the reversal hypothesis. The multiplicative rank stacking erodes signal, Hurst lookback is too short, and raw delta/volume spikes inject noise rather than clean mean-reversion.

**Suggested Improvements**: 1) Replace 1-day delta with industry-neutral 2-5-day capped return to cut noise. 2) Use signed volume-volatility correlation (volume/σ) over 21d instead of 7d rank-rank. 3) Switch Hurst to 252-day with z-score and keep only bottom quartile (anti-persistent). 4) Apply cross-sectional z-score to each term before equal-weight combination instead of nested ranks. 5) Add liquidity filter (ADV>$5M) and sector neutralization; test on 20-day holding with decay.
