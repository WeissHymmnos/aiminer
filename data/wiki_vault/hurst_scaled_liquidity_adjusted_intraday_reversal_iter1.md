---
title: "Hurst-Scaled Liquidity-Adjusted Intraday Reversal"
slug: "hurst_scaled_liquidity_adjusted_intraday_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( (1-Hurst($close,21)) * Delta($close,1) * (1-Corr($volume,$close,5)) * (Mean($volume,3)/Mean($volume,15)-1) ) goes long stocks whose 1-day return is negat…"
updated: "2026-04-14T12:15:28"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0048
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1-Hurst($close,21)) * Delta($close,1) * (1-Corr($volume,$close,5)) * (Mean($volume,3)/Mean($volume,15)-1) ) goes long stocks whose 1-day return is negative, whose 5-day volume-price correlation is low, whose 3-day volume is above its 15-day mean, and whose 21-day Hurst is low (<0.45), expecting that liquidity-seeded intraday reversals are strongest when persistence is weakest.

**Rationale**: Macro: Fed blackout ahead of the May meeting leaves markets pricing a 70 % chance of no cut before September while April CPI is expected to tick up on sticky services; liquidity is drying up with repo rates drifting higher. Market Analysis: implied vol >22 % and intraday ranges >1.8 % for SPY show a choppy, mean-reverting regime. Prior failures show binary Hurst gates concentrate signals; instead we scale the entire alpha by (1-Hurst) so the reversal magnitude fades smoothly as persistence rises, keeping the signal continuous across the full cross-section.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Multiply(Sub(1, Ts_Rank($close, 21)), Delta($close, 1)), Sub(1, Corr($volume, $close, 5))), Sub(Div(Mean($volume, 3), Mean($volume, 15)), 1)))`

**Math Formula**: R_{i,t}=\text{rank}_t\left(\left(1-H_{i,t}^{(21)}\right)\cdot\Delta C_{i,t}^{(1)}\cdot\left(1-\rho_{i,t}^{(V,C,5)}\right)\cdot\left(\frac{\bar{V}_{i,t}^{(3)}}{\bar{V}_{i,t}^{(15)}}-1\right)\right)

**IC / RankIC**: 0.0048 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: IC 0.0048 is below the 0.02 threshold and Rank IC is 0, indicating negligible linear and rank predictive power; Sharpe 0.69 is modest and drawdown -11.8% is acceptable, but the core signal is too weak to trade. The multiplicative structure forces many terms near zero, washing out the intended reversal/liquidity effect. Hurst is mis-specified (Ts_Rank instead of Hurst exponent), and the volume spike term is unbounded and noisy.

**Suggested Improvements**: Replace Ts_Rank($close,21) with a true 21-day Hurst exponent estimate; winsorize each multiplicative term at 1-99% to reduce outliers; convert volume spike to a capped z-score (max ±3); replace the 4-way multiply with a weighted z-score sum (e.g., 0.4·z_rev + 0.3·z_vol_price + 0.3·z_vol_spike - 0.2·z_hurst) so each component contributes independently; add sector/neutralization and liquidity filters (dollar-volume > 5M); test on 1-5 day horizons to confirm reversal timing.
