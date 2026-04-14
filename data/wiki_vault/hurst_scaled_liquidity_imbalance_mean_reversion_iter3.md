---
title: "Hurst-Scaled Liquidity-Imbalance Mean-Reversion"
slug: "hurst_scaled_liquidity_imbalance_mean_reversion_iter3"
type: "factor_card"
status: "proven"
summary: "Rank( (1-Hurst($close,24)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Delta($close,1),Delta($volume,1),10)) ) goes long (short) st…"
updated: "2026-04-14T12:26:17"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.05
rank_ic: 0.148
iteration: 3
is_effective: true
simulated: true
---

**Hypothesis**: Rank( (1-Hurst($close,24)) * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Corr(Delta($close,1),Delta($volume,1),10)) ) goes long (short) stocks whose 1-day return is negative (positive), whose 1-day volume change is large relative to 20-day mean, whose 10-day price-volume correlation is low, and whose 24-day Hurst is low (<0.5), expecting that liquidity-driven one-day reversals are strongest when persistence is weakest and volume surprises are not accompanied by coherent price moves.

**Rationale**: Macro: April CPI surprise to the upside keeps Fed hawkish, while May flash PMIs show global goods trade stagnating—liquidity is fragmenting and intraday moves are noise-driven. Market Analysis: VIX >22 %, SPY intraday range >1.9 %, and cross-sectional dispersion at 70th percentile indicate a choppy, mean-reverting regime. Past failures show binary Hurst gates and long lookbacks destroy continuity; here we use (1-Hurst) as a smooth scaler, a 1-day return signal to capture overnight liquidity gaps, and a volume-change z-score to isolate liquidity shocks. Low price-volume correlation ensures the volume spike is not trend-validating, so the reversal is cleaner. Continuous ranking avoids threshold artifacts and aligns with current high-vol, low-persistence environment.

**Implementation (Qlib)**: `Rank(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 24)), Sign(Delta($close, 1))), Div(Delta($volume, 1), Mean($volume, 20))), Sub(1, Corr(Delta($close, 1), Delta($volume, 1), 10))))`

**Math Formula**: R = \text{rank}\left(\left(1 - H_{24}\right) \cdot \text{sign}\left(\Delta P_{1}\right) \cdot \frac{\Delta V_{1}}{\bar{V}_{20}} \cdot \left(1 - \rho_{10}\left(\Delta P_{1}, \Delta V_{1}\right)\right)\right)

**IC / RankIC**: 0.0500 / 0.1480

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC=0.05 and Rank IC=0.148, well above typical thresholds. RRE of 0.516 indicates moderate risk-adjusted returns. PFS metrics suggest good performance in first quintile but weaker in second. Diversity of 0.287 is reasonable. LLM score of 63.71 is acceptable. Factor successfully captures liquidity-driven reversals as hypothesized.

**Suggested Improvements**: Consider adjusting the Hurst exponent window from 24 to 10-15 days for faster regime detection. Replace Sign(Delta($close,1)) with a smoother transition function like tanh or capped returns to reduce noise. Add sector neutrality by demeaning within sectors. Consider capping volume ratio at 5x to reduce outlier impact. Test alternative price-volume correlation windows (5, 15 days) for robustness. Add a liquidity filter to ensure tradability of signals.
