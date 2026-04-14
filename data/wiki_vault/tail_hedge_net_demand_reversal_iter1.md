---
title: "Tail-Hedge Net Demand Reversal"
slug: "tail_hedge_net_demand_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Over the last 5 trading days, stocks whose cumulative put/call open-interest ratio jumps into the top decile while simultaneously exhibiting the largest single…"
updated: "2026-04-13T20:12:01"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.011
rank_ic: 0.088
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Over the last 5 trading days, stocks whose cumulative put/call open-interest ratio jumps into the top decile while simultaneously exhibiting the largest single-day drop in 25-delta implied-vol skew (i.e. crash premium deflates fastest) tend to rebound over the next 1-5 days; factor = Rank(ΔPutCallOI,5) * (-Rank(Δ25dSkew,1)) so the highest demand-to-hedge paired with the fastest skew collapse scores highest.

**Rationale**: With the Fed on hold and macro data soft, investors are buying downside protection yet dealers are long that tail convexity; when overnight macro shocks fail to materialise the skew deflates quickly, forcing dealers to buy back delta, pushing spot up. Rank-based cross-sectional construction neutralises the broad low-vol grind and isolates the microstructure squeeze created by excess gamma sold to hedgers.

**Implementation (Qlib)**: `Rank(Delta($volume,5),5) * (-Rank(Delta($close,1),1))`

**Math Formula**: R_{i,t+1:t+5} = \alpha + \beta \cdot \text{Factor}_{i,t} + \epsilon_{i,t}\quad\text{where}\quad \text{Factor}_{i,t} = \text{Rank}_t\left(\Delta\text{PutCallOI}_{i,t-5:t},5\right) \cdot \left(-\text{Rank}_t\left(\Delta\text{25dSkew}_{i,t-1:t},1\right)\right)

**IC / RankIC**: 0.0110 / 0.0880

**Effectiveness**: ❌ FAILED

**Review Summary**: IC of 0.011 is below the 0.02 threshold, but Rank IC of 0.088 is encouraging; RRE 0.42 and PFS2 0.69 show some alpha, yet code uses volume/close deltas instead of put/call OI and 25-d skew, so the signal is not testing the stated hypothesis.

**Suggested Improvements**: Replace the proxy variables with actual put/call open-interest data and 25-delta implied-vol skew; verify the 5-day OI change and 1-day skew drop rankings; consider neutralizing sector/market beta and adding liquidity filter to ensure tradability; shorten or lengthen the formation window to 3-10 days to sharpen the contrarian rebound signal.
