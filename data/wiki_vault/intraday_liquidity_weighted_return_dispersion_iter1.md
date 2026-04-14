---
title: "Intraday Liquidity-Weighted Return Dispersion"
slug: "intraday_liquidity_weighted_return_dispersion_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( ( ($close - $open) / ($high - $low + 1e-6) ) * ( $volume / Ts_Mean($volume,10) ) * Sign( Corr($vwap, $close, 5) - Corr($vwap, $close, 20) ) )"
updated: "2026-04-14T12:15:01"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( ( ($close - $open) / ($high - $low + 1e-6) ) * ( $volume / Ts_Mean($volume,10) ) * Sign( Corr($vwap, $close, 5) - Corr($vwap, $close, 20) ) )

**Rationale**: Macro: With the PBoC draining liquidity to defend the yuan and hot-money outflows accelerating, micro-price formation is increasingly driven by local order imbalances rather than fundamental flows; moves that widen intraday range without proportional volume and whose short-term VWAP tracking deteriorates vs longer-term tracking are liquidity mirages. Market regime is high-vol/bear-leaning; intraday reversals dominate. Cross-sectional rank forces continuous ordering and neutralizes beta. The ratio of return to range normalizes for volatility, the volume z-score penalizes low-liquidity outliers, and the correlation-delta sign captures the moment when price is losing short-term fair-value anchorship—an early warning of imminent mean-reversion within 1-2 days.

**Implementation (Qlib)**: `Rank(Mult(Div(Delta($close,0),Delta($high,0)-Delta($low,0)+1e-6),Div($volume,Mean($volume,10))),Mult(Sign(Delta(Corr($vwap,$close,5),Corr($vwap,$close,20))),1))`

**Math Formula**: \text{Rank}\left(\left(\frac{C_t - O_t}{H_t - L_t + 10^{-6}}\right)\cdot\left(\frac{V_t}{\frac{1}{10}\sum_{k=0}^{9}V_{t-k}}\right)\cdot\text{Sign}\left(\text{Corr}(\text{VWAP}_{t-4:t},C_{t-4:t}) - \text{Corr}(\text{VWAP}_{t-19:t},C_{t-19:t})\right)\right)

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows zero IC, Rank IC, RRE and Sharpe, indicating no predictive power; likely caused by the Rank operator collapsing all cross-sectional variation to uniform ranks each period, wiping out signal.

**Suggested Improvements**: Remove outer Rank; winsorize raw values at 1-99% instead. Replace 1e-6 denominator with max(high-low, 0.01*high) to avoid near-zero spikes. Use Ts_Zscore over 20 days on the final composite to standardize, then cap at ±3. Test shorter volume MA (3-5d) and longer correlation deltas (10 vs 30d) to capture faster momentum shifts.
