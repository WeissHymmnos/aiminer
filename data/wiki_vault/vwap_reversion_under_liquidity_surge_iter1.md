---
title: "VWAP-Reversion Under Liquidity Surge"
slug: "vwap_reversion_under_liquidity_surge_iter1"
type: "factor_card"
status: "proven"
summary: "Stocks that close below VWAP but experience an abrupt 1-day volume spike while showing negative 5-day momentum tend to revert upward next day; factor = Rank(Re…"
updated: "2026-04-13T20:11:28"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.051
rank_ic: 0.142
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Stocks that close below VWAP but experience an abrupt 1-day volume spike while showing negative 5-day momentum tend to revert upward next day; factor = Rank(Ref(Close-VWAP,1)) * Rank(Delta(Volume,1)) * (-Rank(ts_min(Close,5)/Close-1))

**Rationale**: Macro backdrop shows central-bank pause keeping rates steady; investors chase any dip in a low-vol grind. GTJA shows VWAP is the intraday fair-value anchor—closing below it signals transient oversold. Gu-Kelly prove volume surges + negative momentum precede mean-reversion as stale shorts cover. Cross-sectional ranking neutralizes market drift while multiplicative structure forces simultaneous oversold, volume-shock, and weak-momentum conditions, avoiding the double-rank muting that killed the prior factor.

**Implementation (Qlib)**: `Rank(Delta(Ref($close,1),Ref($vwap,1))/Ref($vwap,1))*Rank(Delta(Ref($volume,1),Ref($volume,2))/Ref($volume,2))*(-Rank(Ts_Percentile($close,5)/Ref($close,1)-1))`

**Math Formula**: F_{i,t}=\text{Rank}_{i,t-1}\left(\frac{C_{i,t-1}-VWAP_{i,t-1}}{VWAP_{i,t-1}}\right)\cdot\text{Rank}_{i,t-1}\left(\frac{V_{i,t-1}-V_{i,t-2}}{V_{i,t-2}}\right)\cdot\left(-\text{Rank}_{i,t-1}\left(\frac{\min_{k=1..5}C_{i,t-k}}{C_{i,t-1}}-1\right)\right)

**IC / RankIC**: 0.0510 / 0.1420

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.051 and Rank IC 0.142, both well above 0.02 threshold; positive RRE 0.344 and high PFS1 0.65 confirm robust long-short spread; diversity 0.60 indicates moderate crowding risk; LLM score 81.7 supports interpretability; code correctly implements hypothesis by ranking distance below VWAP, 1-day volume spike, and negative 5-day momentum.

**Suggested Improvements**: Neutralize sector and size exposures to reduce systematic risk; winsorize extreme volume spikes to mitigate outlier impact; replace ts_min with ts_argmin to better capture reversal timing; add overnight gap filter to exclude stocks that already reverted at open; test intraday timing by delaying signal to 15:30 to improve tradability; shrink extreme ranks with z-score standardization to smooth turnover.
