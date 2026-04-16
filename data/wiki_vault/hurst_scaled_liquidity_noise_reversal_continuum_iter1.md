---
title: "Hurst-Scaled Liquidity-Noise Reversal Continuum"
slug: "hurst_scaled_liquidity_noise_reversal_continuum_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (1-Hurst($close,20))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Abs(Corr(Delta($close,1),Delta($volume,1),15))) * (Std($close,5…"
updated: "2026-04-16T15:22:50"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "price_volume_data_source", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
parents: ["stat_arb_family"]
depends_on: ["price_volume_data_source", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
ic: -0.0014
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1-Hurst($close,20))^2 * Sign(Delta($close,1)) * (Delta($volume,1)/Mean($volume,20)) * (1-Abs(Corr(Delta($close,1),Delta($volume,1),15))) * (Std($close,5)/Mean($close,20)) ) goes long (short) stocks whose 1-day return is negative (positive), whose 1-day volume surprise is large, whose 15-day price-volume correlation is closest to zero (maximally noisy), whose 5-day price volatility is elevated, and whose 20-day Hurst is lowest, expecting that liquidity-driven one-day reversals are strongest when persistence is weakest, volume moves are uncorrelated with price, and intraday noise is high.

**Rationale**: Macro: May CPI print flat but core services inflation sticky at 0.3 % m/m keeps Fed on hold; meanwhile China exports drop 7 % y/y—global liquidity is shrinking and volume is migrating to idiosyncratic single-stock shocks rather than coherent sector flows. Market Analysis: VIX futures curve inverted, SPY 5-day realized volatility 19 % vs 30-day 15 %, and intraday return skew strongly negative—regime is high-chop with micro-cap outperformance on bursts of noisy volume. By squaring (1-Hurst) we amplify the continuum of mean-reversion signals instead of thresholding, while the cross-sectional Rank ensures a smooth spectrum from most to least attractive reversal candidates.

**Implementation (Qlib)**: `Rank(Mul(Pow(Sub(1, Ts_Rank($close, 20)), 2), Mul(Sign(Delta($close, 1)), Mul(Div(Delta($volume, 1), Mean($volume, 20)), Mul(Sub(1, Abs(Corr(Delta($close, 1), Delta($volume, 1), 15))), Div(Std($close, 5), Mean($close, 20)))))))`

**Math Formula**: RANK\left(\left(1-H_{20}(C)\right)^{2}\cdot\text{sgn}\left(\Delta C_{1}\right)\cdot\frac{\Delta V_{1}}{\bar{V}_{20}}\cdot\left(1-\left|\rho_{15}\left(\Delta C_{1},\Delta V_{1}\right)\right|\right)\cdot\frac{\sigma_{5}(C)}{\bar{C}_{20}}\right)

**IC / RankIC**: -0.0014 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC≈0, Rank IC=0, negative Sharpe. The multiplicative interaction of five weak or noisy terms collapses signal-to-noise; Hurst term is inverted (Ts_Rank vs Hurst), Sign(Delta) flips daily so portfolio turns over without trend, and volume-volatility-correlation interaction dilutes any residual reversal alpha.

**Suggested Improvements**: 1) Replace Ts_Rank($close,20) with proper Hurst exponent (DFA or RS-Hurst) and keep direction low-Hurst → mean-reversion. 2) Drop Sign(Delta) and instead use -Delta($close,1) to directly target reversal. 3) Winsorize each multiplicative term at 1-99 % to curb outliers. 4) Use decile-industry neutral z-scores before combining; sum ranks instead of multiplying to preserve signal. 5) Add liquidity filter (ADV>20 M) and vol-of-vol cap (Std($close,5)/Mean<2) to reduce micro-structure noise. 6) Smooth final composite with 5-day EWMA and hold 2-5 days to cut turnover; target IC>0.02 on next-day return.
