---
title: "Liquidity-Adjusted Hurst-Slope Dispersion Reversal"
slug: "liquidity_adjusted_hurst_slope_dispersion_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( (1 - Hurst($close,30)) * (Slope($close,5) - Median(Slope($close,5), 500)) * (1 - Corr($volume, $close, 3)) * ($volume / Ts_Mean($volume,20) - 1) ) goes l…"
updated: "2026-04-14T12:25:51"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.006
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (1 - Hurst($close,30)) * (Slope($close,5) - Median(Slope($close,5), 500)) * (1 - Corr($volume, $close, 3)) * ($volume / Ts_Mean($volume,20) - 1) ) goes long (short) stocks whose 5-day price slope is far below (above) the cross-sectional median, whose 3-day volume-price correlation is low, whose volume is elevated, and whose 30-day Hurst is low (<0.45), expecting that liquidity-seeded dispersion reversals are strongest when persistence is weakest and intraday ranges are wide.

**Rationale**: Macro: Fed minutes reiterate “higher for longer” with June CPI expected to print 3.1 %, keeping front-end rates >5 % and draining repo liquidity. Trade data show Asia export volumes down 7 % y/y, fragmenting global bid depth. Market Analysis: SPY implied vol >22 %, intraday range >1.8 %, and sector dispersion at 90th percentile—classic choppy, mean-reverting regime. Prior failures show binary Hurst gates and simple volume-spike flags collapse when liquidity evaporates; instead we use (1-Hurst) as a continuous scaler, cross-sectional slope deviation to capture dispersion, and a volume-ratio term that keeps the signal smooth across the entire universe. Continuous ranking avoids threshold cliffs and adapts fluidly as persistence and liquidity drift.

**Implementation (Qlib)**: `Rank(Mul(Mul(Mul(Sub(1, Ts_Rank($close, 30)), Sub(Delta($close, 5), CSRank(Delta($close, 5)))), Sub(1, Corr($volume, $close, 3))), Sub(Div($volume, Mean($volume, 20)), 1)))`

**Math Formula**: R_{i}=\text{Rank}_{i}\left(\left(1-H_{i,30}\right)\cdot\left(S_{i,5}-\widetilde{S}_{\bullet,5,500}\right)\cdot\left(1-C_{i,3}^{(v,p)}\right)\cdot\left(\frac{V_{i}}{\bar{V}_{i,20}}-1\right)\right)

**IC / RankIC**: 0.0060 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows negligible predictive power: IC 0.006 (<<0.02), Rank IC 0.0, RRE 0.57 indicates weak consistency. Sharpe 0.52 is modest but driven by low volatility rather than strong signal. Hypothesis of liquidity-seeded dispersion reversals is not validated.

**Suggested Improvements**: 1) Replace 30-day Hurst with 10-day Hurst on 5-min returns to better capture short-term persistence breakdown. 2) Use z-score of 5-day slope vs 500-day history instead of cross-sectional median to preserve time-series stationarity. 3) Substitute 3-day volume-price correlation with 3-day volume-volatility correlation to isolate liquidity shocks. 4) Apply sector-neutral and cap-neutral residualization before ranking to reduce noise. 5) Add intraday range proxy (high-low/close) as multiplier to amplify dispersion signal. 6) Shrink volume spike term with log transform to reduce extreme outliers.
