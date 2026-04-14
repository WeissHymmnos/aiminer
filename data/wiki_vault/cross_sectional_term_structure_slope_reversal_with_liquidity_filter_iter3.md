---
title: "Cross-Sectional Term-Structure Slope Reversal with Liquidity Filter"
slug: "cross_sectional_term_structure_slope_reversal_with_liquidity_filter_iter3"
type: "factor_card"
status: "failed"
summary: "Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-6)) * Sign(Delta(2yr_swap_rate,1) - Delta(10yr_swap_rate,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, Delta(2y…"
updated: "2026-04-14T12:33:41"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.002
rank_ic: -0.028
iteration: 3
is_effective: false
simulated: true
---

**Hypothesis**: Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-6)) * Sign(Delta(2yr_swap_rate,1) - Delta(10yr_swap_rate,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, Delta(2yr-10yr_swap_spread), 21), 0.6)) * Rank(1 / (1 + realized_vol_20d))

**Rationale**: May CPI printed in-line but the 2s10s swap spread flattened 6bp as the market repriced a shallower Fed cutting path—classic late-cycle signal. Stocks in cyclical industries that sold off on rising volume while the curve flattened are oversold: short-end rates rising faster than long-end tightens financial conditions but also signals peak policy restraint. Cross-sectional rank captures relative sensitivity to the slope shock; dividing by volume isolates liquidity-adjusted moves. Inverting the sign bets on reversal when the curve re-steepens on softer data. Down-weighting high-realized-vol names avoids ongoing earnings shocks; quantile industry correlation ensures continuous sector-neutral exposure to slope-beta rather than binary sector flags.

**Implementation (Qlib)**: `Mul(Rank(Div(Delta($close,5),Add(Delta($volume,5),1e-6))),Sign(Delta(Sub(Ref($close,2),Ref($close,10)),1))),Neg(Rank(Ts_Percentile(Corr(GroupNeutral(Rank($close)),Delta(Sub(Ref($close,2),Ref($close,10)),21),21),60))),Rank(Inv(Add(Std($close,20),1))))`

**Math Formula**: R\left(\frac{\Delta_{5}P_{c}}{\Delta_{5}V+10^{-6}}\cdot\text{sgn}\left(\Delta_{1}r_{2y}-\Delta_{1}r_{10y}\right)\right)\cdot(-1)\cdot R\left(Q_{0.6}\left(\text{Corr}_{21}\left(R_{\text{ind}},\Delta_{21}(r_{2y}-r_{10y})\right)\right)\right)\cdot R\left(\frac{1}{1+\sigma_{20}}\right)

**IC / RankIC**: -0.0020 / -0.0280

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power with IC=-0.002 and Rank IC=-0.028, both below 0.02 threshold. Negative signs suggest potential signal inversion. RRE=0.636 indicates reasonable risk-return efficiency. Diversity=0.786 shows good cross-sectional variation. LLM score=62.64 suggests moderate complexity. Code implementation appears to deviate from hypothesis - using price differences instead of swap rates, and industry return correlation not properly implemented.

**Suggested Improvements**: 1) Fix code to match hypothesis: replace price-based deltas with actual 2yr and 10yr swap rate data, implement proper industry return correlation 2) Consider absolute value or squared terms for swap spread delta to capture magnitude not just direction 3) Test alternative volatility measures (e.g., range-based or GARCH) instead of realized vol 4) Try different lookback windows (10d, 63d) for correlation and volatility components 5) Add sector neutrality to reduce unintended exposures 6) Consider winsorizing extreme values before ranking to reduce noise impact
