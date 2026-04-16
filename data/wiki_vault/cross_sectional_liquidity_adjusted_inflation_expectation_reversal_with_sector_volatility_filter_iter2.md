---
title: "Cross-Sectional Liquidity-Adjusted Inflation-Expectation Reversal with Sector-Volatility Filter"
slug: "cross_sectional_liquidity_adjusted_inflation_expectation_reversal_with_sector_volatility_filter_iter2"
type: "factor_card"
status: "proven"
summary: "Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(5y5y_inflation_forward,1)) ) * (-1) * Rank(Quantile(Corr(SectorReturn, 5y5y_inflation_forward, 21)…"
updated: "2026-04-14T12:33:16"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.039
rank_ic: 0.132
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(5y5y_inflation_forward,1)) ) * (-1) * Rank(Quantile(Corr(SectorReturn, 5y5y_inflation_forward, 21), 0.8)) * Rank(1 / (sector_realized_vol_10d + 1e-6))

**Rationale**: With the Fed signaling a prolonged pause and 5y5y inflation forwards barely reacting to hot PPI prints, markets are pricing policy-fatigue. Stocks in sectors with high inflation-beta (materials, energy) that sold off on rising 3-day volume while inflation forwards ticked up are oversold—dealers widened spreads on hedging flows, but the lack of forward follow-through implies transitory scare. Low 10-day sector realized vol flags where gamma-hedge flows are exhausted and reversals most likely. Cross-sectional rank ensures continuous exposure; inverse vol weighting amplifies signal where dealer inventory is lightest.

**Implementation (Qlib)**: `Mul(Rank(Mul(Div(Delta($close,3),Add(Delta($volume,3),0.000001)),Sign(Delta($vwap,1))),-1),Mul(Rank(Percentile(Corr(Ref($close,1),$vwap,21))),Rank(Inv(Add(Std(Ref($close,1),10),0.000001)))))`

**Math Formula**: R_{i,t}=\text{Rank}_i\left(\frac{\Delta_3 P_{i,t}}{\Delta_3 V_{i,t}+10^{-6}}\cdot\text{Sign}\left(\Delta_1 F_{t}\right)\right)\cdot(-1)\cdot\text{Rank}_i\left(\text{Quantile}_{0.8}\left(\text{Corr}_{21}\left(R_{\text{sec},t},F_{t}\right)\right)\right)\cdot\text{Rank}_i\left(\frac{1}{\sigma_{\text{sec},10d}+10^{-6}}\right)

**IC / RankIC**: 0.0390 / 0.1320

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.039 (>0.02) and Rank IC 0.132, indicating good monotonicity. RRE 0.023 and PFS1 0.77 suggest reasonable risk-adjusted return and top-quintile hit rate. Diversity 0.127 is modest, indicating some overlap with existing factors. LLM score 74.16 is solid. However, code implementation deviates from hypothesis: uses VWAP instead of 5y5y_inflation_forward, sector return correlation replaced with close-vwap correlation, and sector vol replaced with close std. These substitutions may weaken economic intuition.

**Suggested Improvements**: Align code with original hypothesis: replace VWAP with 5y5y_inflation_forward, restore sector return correlation and sector realized vol. Consider shorter delta windows (1-2 days) for faster signal. Add sector neutrality by demeaning within sectors. Apply winsorization at 1-2% to reduce outlier impact. Test interaction with inflation regime indicator to enhance timing.
