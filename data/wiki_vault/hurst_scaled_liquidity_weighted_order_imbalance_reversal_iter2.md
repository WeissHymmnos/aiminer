---
title: "Hurst-Scaled Liquidity-Weighted Order-Imbalance Reversal"
slug: "hurst_scaled_liquidity_weighted_order_imbalance_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,18)) * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,1)),Rank($volume),7)) ) goes long (sh…"
updated: "2026-04-14T12:15:58"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0011
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1-Hurst($close,18)) * Sign(Delta($close,3)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Rank($close/Ref($close,1)),Rank($volume),7)) ) goes long (short) stocks whose 3-day return is negative (positive), whose 1-day volume change is large, whose 7-day price-volume correlation is low, and whose 18-day Hurst exponent is low (<0.45), expecting that liquidity-driven order-imbalance reversals are strongest when persistence is weakest and volume spikes are uncorrelated with price moves.

**Rationale**: Macro: May CPI surprised to the upside (3.4 % vs 3.2 % est) and the Fed dot-plot now shows only one cut in 2024; liquidity is draining with overnight repo printing 5.35 % and primary dealer inventories at 18-month lows. Market Analysis: SPY intraday range >2 % for seven straight sessions, VVIX >110, and cross-sectional 5-day autocorrelation of returns has collapsed to –0.08—classic high-vol, mean-reverting regime. Prior failures show that binary Hurst gates and simple volume-spike flags assign the same score to most stocks; instead we multiply (1-Hurst) to create a smooth persistence decay, scale by signed volume-change to capture liquidity shocks, and use (1-Corr) to isolate stocks where volume is moving against price—an order-imbalance signature that quickly exhausts when persistence is low. The continuous rank output spreads smoothly across the entire universe, avoiding the binary pile-ups that killed earlier iterations.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Multiply(Sub(1, CSRank(Ts_Rank(Log($close), 18))), Sign(Delta(Log($close), 3))), Divide(Delta(Log($volume), 1), Log(Mean($volume, 20)))), Sub(1, Corr(CSRank(Delta(Log($close), 1)), CSRank(Delta(Log($volume), 1)), 7))))`

**Math Formula**: \text{Score}_i = \text{Rank}\left(\left(1 - H_i\right) \cdot \text{sgn}\left(\Delta_3 C_i\right) \cdot \frac{\Delta_1 V_i}{\bar{V}_{20,i}} \cdot \left(1 - \rho_{7,i}\right)\right)

**IC / RankIC**: -0.0011 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows no predictive power: IC and Rank IC are both ~0, Sharpe is negative, and drawdown exceeds 50%. The combined signal appears to cancel itself out—especially the Sign(Delta(close,3)) term that forces half the universe to the wrong side every day.

**Suggested Improvements**: 1) Remove the Sign(Delta(close,3)) term; instead let the reversal signal come from the interaction of volume spike, low Hurst, and low price-volume correlation. 2) Replace 18-day Hurst with a shorter, smoother regime proxy (e.g., 5-day RSI < 30) to better capture anti-persistent episodes. 3) Winsorize volume-change at 1-99 % to curb outliers. 4) Scale all inputs to z-score and form an equal-weighted composite, then cross-sectionally z-score the final alpha. 5) Run sector-neutral and cap-neutral trims, and test holding periods 1-5 days; expect IC > 0.02 before acceptance.
