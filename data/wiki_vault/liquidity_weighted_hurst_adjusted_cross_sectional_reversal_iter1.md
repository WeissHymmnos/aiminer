---
title: "Liquidity-Weighted Hurst-Adjusted Cross-Sectional Reversal"
slug: "liquidity_weighted_hurst_adjusted_cross_sectional_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,14))^2 * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,5)),Rank($volume),7)) ) goes long s…"
updated: "2026-04-14T12:25:25"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1-Hurst($close,14))^2 * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,5)),Rank($volume),7)) ) goes long stocks whose 3-day return is negative, whose 1-day volume change is positive, whose 7-day price-volume correlation is low, and whose 14-day Hurst is low; the squared Hurst term amplifies the signal in strongly mean-reverting regimes while the volume-change term scales liquidity shock size.

**Rationale**: Macro: April CPI surprise upside (3.8 % vs 3.6 %) keeps Fed hawkish, repo rates 15 bp above mid-rate, primary-dealer inventories at 5-yr low—liquidity is drying up and intraday ranges >2 %. Market Analysis: implied vol 24 %, VVIX>110, cross-sectional dispersion at 80th %-ile—classic choppy bear with frequent micro-reversals. Prior failures show binary Hurst gates kill continuity; using (1-Hurst)^2 keeps signal smooth and strongest when mean-reversion is most reliable. Liquidity shock (Delta vol) interacts with price-volume decorrelation to capture transient order-flow imbalances that quickly exhaust in low-persistence markets.

**Implementation (Qlib)**: `Rank(Mul(Pow(Sub(1, Mean(Ref($close, 1), 14)), 2), Mul(Sign(Delta($close, 3)), Div(Delta($volume, 1), Mean($volume, 20)))), Sub(1, Corr(Rank(Div($close, Ref($close, 5))), Rank($volume), 7)))`

**Math Formula**: R_{i}=\text{Rank}_i\left(\left(1-H_{i,14}\right)^2\cdot\text{sgn}\left(C_{i,t}-C_{i,t-3}\right)\cdot\frac{V_{i,t}-V_{i,t-1}}{\bar{V}_{i,20}}\cdot\left(1-\text{Corr}_7\left(\text{Rank}\left(\frac{C_{i,t}}{C_{i,t-5}}\right),\text{Rank}\left(V_{i,t}\right)\right)\right)\right)

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: All metrics are zero, indicating the factor has no predictive power; the implementation appears to have a critical bug (mean of Ref($close,1) is not Hurst exponent) and the formula structure collapses the signal to a constant or NaN.

**Suggested Improvements**: Replace Mean(Ref($close,1),14) with a proper 14-day Hurst exponent estimate (e.g., RS or DFA method); add tiny constant to Div denominator to avoid division by zero; verify sign and rank operations do not map entire cross-section to identical values; test on a small date window with raw inputs to confirm non-zero variance before full backtest.
