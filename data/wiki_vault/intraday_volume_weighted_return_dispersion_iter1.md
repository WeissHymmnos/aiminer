---
title: "Intraday Volume-Weighted Return Dispersion"
slug: "intraday_volume_weighted_return_dispersion_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( (Ts_Mean($close - $vwap, 3) / (Std($close - $vwap, 3) + 1e-6)) * Sign(Delta($volume,1)) ) ranks stocks by how far and consistently their closing prints d…"
updated: "2026-04-14T12:25:25"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.008
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (Ts_Mean($close - $vwap, 3) / (Std($close - $vwap, 3) + 1e-6)) * Sign(Delta($volume,1)) ) ranks stocks by how far and consistently their closing prints drift from VWAP over 3 days, scaled by intraday dispersion and signed by concurrent volume change; it goes long stocks whose closing price persistently sits above VWAP with rising volume and short those closing below VWAP with rising volume, expecting that sustained volume-validated divergence signals informed momentum that persists for 1-2 days.

**Rationale**: Macro: With the Fed on extended pause and inflation sticky, liquidity is shrinking; moves where closing price keeps diverging from VWAP accompanied by rising volume are more likely to reflect informed flow rather than noise. Market regime is high-vol/bearish; intraday auctions become decisive. Cross-agent lesson: raw price/volume ratios failed (IC<0.01) because they ignored intraday benchmark; using VWAP as fair-price anchor and 3-day mean/dispersion captures persistence while rank neutralizes market beta. The signal is continuous across the universe and exploits volume-confirmed micro-price pressure that takes time to be fully impounded.

**Implementation (Qlib)**: `Rank(Mul(Div(Mean(Sub($close, $vwap), 3), Add(Std(Mean(Sub($close, $vwap), 3), 3), 0.000001)), Sign(Delta($volume, 1))))`

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\frac{\frac{1}{3}\sum_{k=0}^{2}(C_{i,t-k}-VWAP_{i,t-k})}{\sqrt{\frac{1}{3}\sum_{k=0}^{2}(C_{i,t-k}-VWAP_{i,t-k}-\mu_i)^2}+10^{-6}}\cdot\text{Sign}(V_{i,t}-V_{i,t-1})\right)

**IC / RankIC**: 0.0080 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.008 is below the 0.02 threshold and Rank IC is 0, indicating negligible linear or rank predictive power; Sharpe 0.91 is driven by low-vol exposure rather than alpha. The 3-day mean/std normalization is too short to stabilize the signal, and signing by single-day volume change injects noise. VWAP drift is better captured with longer windows and volume confirmation over 5-10 days.

**Suggested Improvements**: Extend Ts_Mean and Std to 5-10 days; replace Sign(Delta($volume,1)) with Ts_Zscore($volume,5) to smooth volume confirmation; winsorize the raw divergence at 1-99% to curb outliers; test sector-neutral version to isolate stock-specific drift; add overnight gap adjustment so signal uses open-to-close vs VWAP only.
