---
title: "Hurst-Filtered Liquidity-Volatility Divergence Reversal"
slug: "hurst_filtered_liquidity_volatility_divergence_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( If(Hurst($close,30)∈[0.3,0.55], -1, 0) * Sign(Delta($close,2)) * (Std($volume,5)/Mean($volume,20)-1) * (1-Corr(Rank(Delta($close,1)),Rank(Delta($volume,1…"
updated: "2026-04-14T12:08:25"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0011
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( If(Hurst($close,30)∈[0.3,0.55], -1, 0) * Sign(Delta($close,2)) * (Std($volume,5)/Mean($volume,20)-1) * (1-Corr(Rank(Delta($close,1)),Rank(Delta($volume,1)),10)) ) goes long (short) stocks whose 10-day price-volume change correlation is low, whose 5-day volume volatility is in the top (bottom) quintile relative to its 20-day mean, whose 2-day price move is negative (positive), but only when the 30-day Hurst exponent signals moderate mean-reversion (0.3-0.55), expecting that volume-volatility shocks in lightly persistent markets exhaust and reverse quickly.

**Rationale**: Macro: Fed minutes hint at a prolonged pause with inflation still above target, while global trade volumes contract—liquidity is fragmenting and intraday moves are increasingly noise-driven. Market Analysis shows realized vol >85-percentile and breadth negative, a regime where pure time-series momentum fails but cross-sectional relative trades survive. Prior agent failures reveal that (i) volume-spike filters alone get stuck in crowded reversals, (ii) Hurst windows must be shorter (30d) to capture the current semi-choppy regime, and (iii) using volume volatility instead of raw surge avoids liquidity mirages. Academic base: Kakushadze Alpha 012 & 028 show that volume-volatility divergence predicts reversal; cross-sectional ranking neutralizes market-wide moves. By combining low price-volume correlation with elevated volume volatility and a moderate Hurst band, we isolate liquidity shocks that are likely to mean-revert within days.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Multiply(If(And(GreaterEqual(Ts_Rank($close,30),0.3),LessEqual(Ts_Rank($close,30),0.55)),-1,0),Sign(Delta($close,2))),Subtract(Divide(Std($volume,5),Mean($volume,20)),1)),Subtract(1,Corr(Rank(Delta($close,1)),Rank(Delta($volume,1)),10))))`

**Math Formula**: R=\operatorname{Rank}\left(\left[\mathbb{1}_{[0.3,0.55]}\left(H_{30}\right)\cdot(-1)\right]\cdot\operatorname{sgn}\left(\Delta_{2}P\right)\cdot\left(\frac{\sigma_{5}V}{\mu_{20}V}-1\right)\cdot\left(1-\rho_{10}\left(\operatorname{Rank}(\Delta_{1}P),\operatorname{Rank}(\Delta_{1}V)\right)\right)\right)

**IC / RankIC**: -0.0011 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is ineffective: IC≈0, Rank IC=0, negative Sharpe (-0.22) and deep drawdown (-53%). The Hurst filter plus price-volume interaction produces no predictive power.

**Suggested Improvements**: 1) Replace hard Hurst range with percentile-of-universe or z-score to allow dynamic mean-reversion regimes. 2) Flip the sign on the volume-volatility term: current top-quintile vol expansion is shorted but empirically continues to outperform; go long high vol-shock instead. 3) Shorten correlation window from 10 to 3-5 days to capture transient dislocations. 4) Cap or winsorize all sub-components at 1-2% to curb outliers. 5) Add sector/neutral ranks before final aggregation to isolate stock-specific volume shocks.
