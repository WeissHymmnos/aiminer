---
title: "Intraday Volume-Weighted Return Dispersion Reversal"
slug: "intraday_volume_weighted_return_dispersion_reversal_iter3"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (TsMean($close,5) - TsMean($vwap,5)) / Std($volume,5)  Sign(Corr(Delta($close,3), Delta($volume,3), 10)) ) goes long (sho…"
updated: "2026-04-11T20:47:27.028743"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ts_Mean($close,5) - Ts_Mean($vwap,5)) / Std($volume,5) * Sign(Corr(Delta($close,3), Delta($volume,3), 10)) ) goes long (short) stocks whose 5-day average closing price is above (below) their 5-day volume-weighted average price, scaled by volume volatility, and whose 3-day price-volume correlation is positive (negative), expecting 3-day mean-reversion when price deviates from efficient VWAP without supportive volume alignment.
**Rationale**: In the current high-volatility bearish regime, intraday price moves that drift far from VWAP without corresponding volume confirmation are likely driven by transient order-flow shocks rather than fundamental repricing. When the 5-day average close exceeds VWAP but the 3-day price-volume correlation is positive, it signals that rising prices are accompanied by rising volume—yet the divergence indicates impatient buyers lifting offers. Conversely, negative correlation with price below VWAP suggests capitulation selling. Both extremes revert as liquidity providers arbitrage the dispersion, especially when macro uncertainty (e.g., Fed pause rhetoric) keeps risk premia elevated and encourages quick scalping of dislocations.
**Implementation (Qlib)**: `Rank(Mult(Div(Minus(Mean($close,5),Mean($vwap,5)),Std($volume,5)),Sign(Corr(Delta(Ref($close,3),1),Delta(Ref($volume,3),1),10))))`
**Math Formula**: R = \text{rank}\left( \frac{ \text{mean}_{t=0}^{4}(C_t) - \text{mean}_{t=0}^{4}(V_t) }{ \text{std}_{t=0}^{4}(Q_t) } \cdot \text{sign}\left( \text{corr}_{k=0}^{9}\left( C_{k-3}-C_{k}, Q_{k-3}-Q_{k} \right) \right) \right)
**IC / RankIC**: -0.0029 / -0.0049
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows weak negative IC (-0.0029) and Rank IC (-0.0049), both far below the 0.02 threshold, indicating no predictive power. Sharpe is negative (-0.34) and max drawdown is -14.9%. All other metrics (RRE, PFS, Diversity, LLM Score) are zero, suggesting no alpha generation or robustness. The hypothesis of 3-day mean-reversion post VWAP deviation lacks empirical support in this formulation.
**Suggested Improvements**: 1) Shorten the lookback for mean-reversion signals (e.g., 2-day delta instead of 3-day). 2) Replace volume standardization with dollar-volume or relative volume to better capture liquidity shocks. 3) Add sector/market-neutralization to isolate stock-specific effects. 4) Test asymmetric thresholds (e.g., only trade extreme deciles). 5) Introduce a volatility filter to avoid trading during high-vol regimes. 6) Consider using signed volume (buy/sell imbalance) instead of raw volume correlation.
