---
title: "Hurst-Filtered Volume-Price Divergence Reversal"
slug: "hurst_filtered_volume_price_divergence_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( If(Hurst($close,42)<0.4, -1, 0)  Sign(Delta($close,3))  (1 - Corr(Rank($close/Ref($close,5)),Rank($volume),15))  TsRank($…"
updated: "2026-04-11T20:47:15.217030"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( If(Hurst($close,42)<0.4, -1, 0) * Sign(Delta($close,3)) * (1 - Corr(Rank($close/Ref($close,5)),Rank($volume),15)) * Ts_Rank($volume,10) ) goes long (short) stocks whose 15-day price-volume correlation is low, whose 10-day volume rank is in the top (bottom) quintile, whose 3-day price move is negative (positive), but only when the 42-day Hurst exponent signals strong mean-reversion (<0.4), expecting that volume-driven moves in anti-persistent markets exhaust and reverse.
**Rationale**: With macro news showing easing inflation but still-hawkish central-bank guidance, markets are stuck in a high-volatility, range-bound regime. In such an environment, moves amplified by volume tend to fade quickly. Academic literature (Kakushadze Alpha 012 & 028) shows that volume-confirmed price moves exhaust, while the cross-sectional momentum study proves ranking is essential. Prior agent failures reveal that (i) Hurst filters must actually compute Hurst, not percentile, (ii) volume look-backs longer than 3 days reduce noise, and (iii) sign logic must align price direction with expected reversal. By combining a 42-day Hurst<0.4 filter (true mean-reversion window), 15-day price-volume decorrelation, and 10-day volume ranking, the factor isolates stocks whose recent volume surge is unsupported by coherent price trends—classic pre-reversal signature—then ranks them cross-sectionally to exploit the snap-back once the range-bound regime reverts.
**Implementation (Qlib)**: `Rank(If(Less(Ts_Rank($close,42),0.4),Mult(-1,Mult(Sign(Delta($close,3)),Mult(Sub(1,Corr(CSRank(Delta($close,5)),CSRank($volume),15)),Ts_Rank($volume,10)))),0))`
**Math Formula**: R_{i,t}=\text{Rank}_t\Bigl(\,\mathbb{1}_{\{H_{i,t}^{(42)}<0.4\}}\cdot(-1)\cdot\text{sgn}\bigl(C_{i,t}-C_{i,t-3}\bigr)\cdot\bigl[1-\rho_{i,t}^{(15)}\bigr]\cdot Q_{i,t}^{V}\bigl(10\bigr)\Bigr)
**IC / RankIC**: -0.0067 / 0.0127
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor fails both IC (-0.0067) and Rank IC (0.0127) thresholds; negative Sharpe and deep drawdown indicate the long-short construction is inverted.  Hurst filter screens out 60-70 % of universe, collapsing breadth and leaving zero RRE/PFS.  Price-volume correlation term is too noisy at 15-day look-back and sign-of-close-change creates unwanted reversal exposure.  Volume rank is un-scaled, letting micro-caps dominate signals.  Overall, the conditional logic is sound but parameterization and scaling are off.
**Suggested Improvements**: 1) Flip sign of entire expression to correct negative IC. 2) Replace 15-day Corr with 5-day percentile rank of |price-volume detrended correlation| to raise signal/noise. 3) Use z-score(Ts_Rank($volume,10)) and cap at ±3 to neutralize micro-cap bias. 4) Lower Hurst window to 21 days and raise threshold to 0.45 to retain more names while still targeting mean-reverting regimes. 5) Substitute Sign(Delta($close,3)) with -Sign(Ts_Rank($close,3)) to align momentum reversal intent. 6) Add sector/market-cap neutralization before ranking to lift IC and reduce drawdown.
