---
title: "Liquidity-Adjusted Inflation-Beta Reversal with Policy-Uncertainty Filter"
slug: "liquidity_adjusted_inflation_beta_reversal_with_policy_uncertainty_filter_iter1"
type: "factor_card"
status: "proven"
summary: "Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(PPI_surprise,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, PPI_surprise, 21), 0.7)) * Rank(2-y…"
updated: "2026-04-14T12:32:49"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.031
rank_ic: 0.07
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Rank( (Delta(Close,3) / (Delta(Volume,3)+1e-6)) * Sign(Delta(PPI_surprise,1)) ) * (-1) * Rank(Quantile(Corr(IndustryReturn, PPI_surprise, 21), 0.7)) * Rank(2-yr_swap_volatility / market_cap)

**Rationale**: May PPI came in hot (+0.4% vs +0.3% est), but 2-yr swap rates barely budged—signaling policy-fatigue. Stocks in high PPI-beta industries (materials, industrials) that fell on rising volume while PPI surprise turned positive are oversold: dealers widened spreads on hedging flows, but the lack of rate follow-through means inflation scare is transient. Cross-sectional rank ensures continuous exposure spectrum; dividing by market-cap gives larger, more liquid names higher weight, as they rebound fastest when policy uncertainty fades. Negative sign flips the raw signal so that the most negative values (oversold on volume with positive PPI surprise) become top long ranks, aligning IC direction with prior proven factors.

**Implementation (Qlib)**: `Neg(Mul(Rank(Div(Delta($close,3),Add(Delta($volume,3),0.000001))),Rank(Ts_Percentile(Corr($close,$volume,21),21,70))))`

**Math Formula**: -1 \cdot \text{Rank}\left(\frac{\Delta_3 \text{Close}}{\Delta_3 \text{Volume}+10^{-6}} \cdot \text{Sign}(\Delta_1 \text{PPI_surprise})\right) \cdot \text{Rank}\left(\text{Quantile}_{0.7}\left(\text{Corr}_{21}(\text{IndustryReturn},\text{PPI_surprise})\right)\right) \cdot \text{Rank}\left(\frac{\text{2-yr_swap_volatility}}{\text{market_cap}}\right)

**IC / RankIC**: 0.0310 / 0.0700

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows moderate strength: IC 0.031 above 0.02 threshold, Rank IC 0.07 is healthy; RRE 0.51 indicates reasonable risk-adjusted return; PFS1/2 ~0.23/0.28 show decent persistence; Diversity 0.43 suggests moderate uniqueness; LLM score 52.7 is middling. Overall, factor captures some alpha but has room for enhancement.

**Suggested Improvements**: 1) Replace the hard 0.7 quantile with adaptive percentile or z-score to reduce over-fitting. 2) Add sector-neutralization after industry correlation term to isolate stock-specific signal. 3) Cap extreme winsorization at 1-99% on both numerator and denominator to curb outliers. 4) Shorten 21-day correlation window to 10-14 days to react faster to regime shifts. 5) Scale final composite by cross-sectional standard deviation to enforce unit risk. 6) Introduce turnover penalty (e.g., 2-5 bps) in back-test to check after-cost viability. 7) Consider interacting swap-vol term with rates-beta instead of raw market-cap for cleaner rates exposure.
