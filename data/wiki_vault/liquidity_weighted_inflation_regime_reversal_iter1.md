---
title: "Liquidity-Weighted Inflation-Regime Reversal"
slug: "liquidity_weighted_inflation_regime_reversal_iter1"
type: "experiment_card"
status: "failed"
summary: "Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-5)) * Sign(Delta(PPI_yoy,1)) * (-1) * Rank( (AvgDailyDollarVolume(21) / market_cap) * (1 + 2-yr_swap_rate_vol(5)) )…"
updated: "2026-04-16T15:22:50"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base", "information_coefficient_metric", "rank_ic_metric", "price_volume_data_source", "cross_sectional_long_short_execution"]
node_type: "factor_experiment"
evidence_level: "theory"
parents: ["stat_arb_family"]
depends_on: ["price_volume_data_source", "cross_sectional_long_short_execution"]
risk_flags: []
metrics_ref: ["information_coefficient_metric", "rank_ic_metric"]
ic: 0.0052
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (Delta(Close,5) / (Delta(Volume,5)+1e-5)) * Sign(Delta(PPI_yoy,1)) * (-1) * Rank( (AvgDailyDollarVolume(21) / market_cap) * (1 + 2-yr_swap_rate_vol(5)) ) )

**Rationale**: May PPI printed hot for a third straight month (+0.4 % vs +0.3 % est) while 2-yr swap volatility collapsed, signalling the market no longer believes the Fed will chase headline prints. Stocks that fell on rising 5-day volume while PPI surprise turned positive are now oversold—dealers hedged the inflation scare, but with swap vol fading the macro risk premium is transient. Weighting the reversal by the stock’s own liquidity (share-turnover) times current swap-vol penalises crowded small-caps and rewards large, liquid names that rebound fastest when policy uncertainty fades. Cross-sectional rank keeps the signal continuous across the full universe and neutralises market-level drift.

**Implementation (Qlib)**: `Rank(Mul(Div(Delta($close,5),Add(Delta($volume,5),0.00001)),Mul(Sign(Delta($close,1)),Neg(Rank(Mul(Div(Mean(Mul($volume,$vwap),21),$close),Add(1,Std($close,5))))))))`

**Math Formula**: R\left(\frac{\Delta C_{5}}{\Delta V_{5}+10^{-5}}\cdot\mathrm{sgn}(\Delta P_{1})\cdot(-1)\cdot R\left(\frac{D_{21}}{M}\cdot(1+S_{5})\right)\right)

**IC / RankIC**: 0.0052 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.0052 and Rank IC 0.0 are far below the 0.02 threshold, indicating negligible predictive power; high RRE (0.87) suggests the signal is largely a noisy rebalance effect rather than alpha. Sharpe 0.59 and modest drawdown are not sufficient to override the weak IC. The construction mixes price-momentum, volume-delta, an unintended price-sign term, and a leveraged vol-scaled liquidity ratio in a single rank, diluting any macro PPI signal and amplifying noise.

**Suggested Improvements**: 1) Replace the erroneous Sign(Delta($close,1)) with the intended Sign(Delta(PPI_yoy,1)) macro term. 2) Normalize each sub-term (momentum, volume change, macro surprise, liquidity ratio) into sector-neutral z-scores before combining to reduce collinearity and improve robustness. 3) Shrink or winsorize extreme tails at 1-2% to cut noise and lower RRE. 4) Test a simpler version: z-score(Delta(close,5)/(Delta(volume,5)+ε)) × z-score(Delta(PPI_yoy,1)) × -1, then verify IC>0.02 before adding secondary liquidity or vol terms. 5} Run rolling 252-day IC decay and lag analysis to choose optimal holding period; if IC fades after 5 days, switch to a 1-5 day signal. 6) Verify turnover: if RRE stays >0.7 after fixes, apply either a 2-day smoothing or a 0.4 shrinkage toward previous weights to cut costs.
