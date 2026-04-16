---
title: "Liquidity-Adjusted Hurst-Weighted Idiosyncratic Reversal"
slug: "liquidity_adjusted_hurst_weighted_idiosyncratic_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,15))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Ref(Mean($volume,30),1)) * (1-Abs(Corr(Delta($close,1),Delta($vwap,1),5))) ) goes long…"
updated: "2026-04-14T12:32:46"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.133
rank_ic: -0.006
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Rank( (1-Hurst($close,15))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Ref(Mean($volume,30),1)) * (1-Abs(Corr(Delta($close,1),Delta($vwap,1),5))) ) goes long (short) stocks whose 1-day return is negative (positive), whose 1-day volume change is large vs 30-day average, whose 5-day price-vwap correlation is low, and whose 15-day Hurst is low; the squared Hurst term amplifies mean-reversion when persistence is weakest while the decorrelation term isolates idiosyncratic moves.

**Rationale**: Macro: May CPI print flat but Fed dots still hint at two more hikes in 2026; global export orders slump to 47.3 PMI—liquidity is drying up and moves are increasingly stock-specific. Market Analysis: VIX 24 %, SPY intraday range 2.1 %, sector dispersion at 2023 highs—noise dominates signal. Low Hurst (<0.45) regimes show faster reversal; volume spikes without coherent vwap correlation flag liquidity shocks rather than informed flow. Squaring (1-Hurst) concentrates weight in the choppiest names, producing a smooth cross-sectional rank that avoids the binary filter failures seen in prior 0.3-0.55 windows.

**Implementation (Qlib)**: `Rank(Pow(Sub(1, Ts_Rank($close, 15)), 2) * Sign(Delta($close, 1)) * Div(Delta($volume, 1), Mean(Ref($volume, 1), 30)) * Sub(1, Abs(Corr(Delta($close, 1), Delta($vwap, 1), 5))))`

**Math Formula**: R = \text{rank}\left(\left(1 - H_{15}(C)\right)^2 \cdot \text{sign}\left(\Delta_1 C\right) \cdot \frac{\Delta_1 V}{\mu_{30}(V)} \cdot \left(1 - \left|\rho_{5}\left(\Delta_1 C, \Delta_1 \text{vwap}\right)\right|\right)\right)

**IC / RankIC**: 0.1330 / -0.0060

**Effectiveness**: ❌ FAILED

**Review Summary**: Strong positive IC (0.133) but negligible and negative Rank IC (-0.006) indicates the factor predicts magnitude well but rank ordering poorly; high RRE (0.813) and good PFS show stable long-short spread, yet diversity is moderate. The squared Hurst term may overweight noisy mean-reversion and the sign flip on close return creates a short-biased signal that hurts rank performance.

**Suggested Improvements**: Replace squared Hurst with a signed power (e.g., Hurst^0.5) to reduce noise amplification; flip the sign of the close-return term to align long positions with positive past return and short with negative, restoring positive Rank IC; cap volume-change at ±3σ to mitigate outliers; shorten Hurst window to 10 days and correlation window to 3 days for faster adaptation; finally, winsorize all sub-components at 1-99 pct before ranking to improve robustness.
