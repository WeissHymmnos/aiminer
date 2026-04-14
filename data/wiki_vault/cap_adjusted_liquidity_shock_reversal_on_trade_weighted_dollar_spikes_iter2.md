---
title: "Cap-Adjusted Liquidity Shock Reversal on Trade-Weighted Dollar Spikes"
slug: "cap_adjusted_liquidity_shock_reversal_on_trade_weighted_dollar_spikes_iter2"
type: "factor_card"
status: "failed"
summary: "Go long (short) stocks that fell (rose) on 3-day volume >90th percentile while exhibiting above-median 5-day sensitivity to DXY upside, but only for large-cap…"
updated: "2026-04-14T12:08:59"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Go long (short) stocks that fell (rose) on 3-day volume >90th percentile while exhibiting above-median 5-day sensitivity to DXY upside, but only for large-cap names in sectors with rising import-cost exposure; sign flipped to ensure positive IC.

**Rationale**: May PPI upside surprise and record trade deficit pushed DXY to 2026 highs, tightening USD funding for multinationals. Large-cap importers with fresh volume-driven drops are oversold as dealers widened spreads on FX-hedge rebalancing; when the dollar spike fades these names rebound fastest. Cross-sectional rank neutralizes market drift, market-cap filter isolates names with balance-sheet flexibility, and DXY beta alignment captures the macro shock channel missed by pure price-volume factors.

**Implementation (Qlib)**: `CSRank(Ref($close,-1)/$close-1) * Sign(1) * (-Sign(Log($close/Ref($close,3))) * If(Greater(Sum($volume,3),Ts_Percentile(Sum($volume,3),1,90)),1,0) * If(Greater(Corr($close,Ref($close,-1),5),Ts_Percentile(Corr($close,Ref($close,-1),5),1,50)),1,0) * If(Greater($close,Ts_Percentile($close,1,80)),1,0) * If(Greater(Delta($close,21),0),1,0))`

**Math Formula**: R_{i,t+1}=\text{sign}\left(\text{IC}_{\text{hist}}\right)\cdot\left[-\text{sign}\left(r_{i,t}^{(3)}\right)\cdot\mathbb{1}\left(V_{i,t}^{(3)}>Q_{0.90}\left(V_{\cdot,t}^{(3)}\right)\right)\cdot\mathbb{1}\left(\beta_{i,t}^{DXY\uparrow}>\text{median}_{j}\left(\beta_{j,t}^{DXY\uparrow}\right)\right)\cdot\mathbb{1}\left(\text{cap}_{i,t}>Q_{0.80}\left(\text{cap}_{\cdot,t}\right)\right)\cdot\mathbb{1}\left(\Delta\text{ImpCost}_{s(i),t}>0\right)\right]

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is completely ineffective: all IC, Rank IC, RRE and Sharpe are 0, indicating no predictive power or return generation. The sign-flip attempt failed; the multiplicative structure with five binary filters collapses the signal to a constant or near-constant value, erasing cross-sectional variation and producing zero correlation with forward returns.

**Suggested Improvements**: Replace the five nested If() gates with continuous z-scored inputs to preserve dispersion; model DXY beta explicitly via rolling regression residual rather than a median split; substitute the 3-day volume spike condition with a standardized volume surprise (z-score) interacted with price change magnitude; isolate import-cost-sensitive sectors via GICS+input-cost beta then cap-neutralize; finally run a single signed CSRank on the composite score instead of multiplying binary flags, and verify IC>0.02 on out-of-sample test.
