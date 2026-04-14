---
title: "VWAP-Slipage Liquidity Vacuum Reversion"
slug: "vwap_slipage_liquidity_vacuum_reversion_iter2"
type: "factor_card"
status: "failed"
summary: "Rank( Delta($close,1) / (Std($volume,5)*Abs($close-$vwap)+1e-6) * Sign(Corr($volume,$close-$vwap,3)) ) goes long stocks whose 1-day price change is large relat…"
updated: "2026-04-14T12:08:47"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0055
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Rank( Delta($close,1) / (Std($volume,5)*Abs($close-$vwap)+1e-6) * Sign(Corr($volume,$close-$vwap,3)) ) goes long stocks whose 1-day price change is large relative to the volume volatility–weighted distance from VWAP and whose 3-day volume is positively correlated with intraday slippage, expecting that liquidity-starved moves away from fair value quickly snap back when volume returns.

**Rationale**: Macro: PBoC’s surprise repo cut injects short-term liquidity but global PMI contraction keeps risk-off; intraday moves driven by algorithmic slippage dominate. Market regime is choppy/whiplash—mean-reversion windows shrink to 1 day. Std(volume) scales denominator by liquidity uncertainty; multiplying by |close-vwap| penalizes moves that drift from fair price. Sign(Corr(volume, slippage)) filters for situations where rising volume accompanies widening vwap gap—classic liquidity vacuum. Rank neutralizes beta and avoids prior failures that used raw volume deltas. Hybrid structure exploits microstructure friction before macro re-pricing resumes.

**Implementation (Qlib)**: `Rank(Delta($close,1) / (Std($volume,5) * Abs($close - $vwap) + 1e-6) * Sign(Corr($volume,Abs($close - $vwap),3)))`

**Math Formula**: R_{t}=\text{Rank}\left(\frac{\Delta P_{t,1}}{\left(\sigma_{V,t,5}\cdot|P_{t}-VWAP_{t}|+10^{-6}\right)}\cdot\text{Sign}\left(\rho_{t,3}\left(V,|P-VWAP|\right)\right)\right)

**IC / RankIC**: 0.0055 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: IC 0.0055 far below 0.02 threshold and Rank IC 0.0 indicate no monotonic predictive power; RRE=1.0 shows perfect over-fitting; Sharpe 0.72 is driven by high turnover rather than signal strength.  The factor is essentially noise.

**Suggested Improvements**: Replace 1-day delta with 3-5 day return to reduce noise; winsorize all inputs at 1-99 % to curb outliers; use log(volume) and dollar-volume instead of raw volume; switch 3-day corr to 5-day and demand |corr|>0.3 before applying Sign; add sector-neutral Rank within each GICS group; finally scale final alpha by inverse 20-day volatility to dampen high-turnover names.
