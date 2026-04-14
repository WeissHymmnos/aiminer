---
title: "VWAP-Deviation Liquidity Surge Reversal"
slug: "vwap_deviation_liquidity_surge_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that close far above their VWAP on sharply rising volume but with deteriorating order-flow imbalance (buy-initiated volume shrinking) tend to mean-rever…"
updated: "2026-04-13T20:11:28"
tags: ["专注非线性因子合成与交叉验证的机器学习专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.098
rank_ic: 0.017
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that close far above their VWAP on sharply rising volume but with deteriorating order-flow imbalance (buy-initiated volume shrinking) tend to mean-revert the next day; factor = Rank((Close-VWAP)/VWAP) * Rank(Delta(Volume,1)) * (-Rank(Delta(BuyVolumeRatio,3))) where BuyVolumeRatio is approximated by (Close-Open)/(High-Low).

**Rationale**: With the central bank on hold and macro uncertainty elevated, intraday chasing becomes fragile. GTJA shows VWAP-deviation flags over-extension, while Gu-Kelly proves volume spikes without sustained buy-imbalance foreshadow reversals. Cross-sectional ranking neutralizes the bear-market drift, isolating microstructure exhaustion where late buyers face asymmetric liquidity withdrawal.

**Implementation (Qlib)**: `Rank(Delta($close,0)/$vwap)*Rank(Delta($volume,1)/Ref($volume,1))*(-Rank(Delta((Delta($close,0)/Delta($high,0)-Delta($low,0)),3)/Ref((Delta($close,0)/Delta($high,0)-Delta($low,0)),3)))`

**Math Formula**: F_{i,t}=\text{Rank}_t\left(\frac{C_{i,t}-VWAP_{i,t}}{VWAP_{i,t}}\right)\cdot\text{Rank}_t\left(\frac{V_{i,t}}{V_{i,t-1}}-1\right)\cdot\left(-\text{Rank}_t\left(\frac{\frac{C_{i,t}-O_{i,t}}{H_{i,t}-L_{i,t}}}{\frac{C_{i,t-3}-O_{i,t-3}}{H_{i,t-3}-L_{i,t-3}}}-1\right)\right)

**IC / RankIC**: 0.0980 / 0.0170

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong IC (0.098) but weak Rank IC (0.017), indicating good directional signal but poor rank ordering. High RRE (0.617) suggests robustness. PFS metrics near 0.5 indicate weak predictive power. Low diversity (0.025) suggests overlap with existing factors. LLM score of 92.22 indicates good code quality.

**Suggested Improvements**: 1) Replace BuyVolumeRatio proxy with actual order-flow imbalance data from TAQ or NASDAQ TotalView. 2) Add sector/neutralization to reduce systematic bias. 3) Consider longer lookback periods (5-10 days) for volume and order-flow changes. 4) Add volatility adjustment (divide by realized volatility). 5) Test asymmetric versions (separate up/down days). 6) Add liquidity filter (minimum daily dollar volume).
