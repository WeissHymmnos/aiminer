---
title: "Volume-Accelerated Intraday Reversal with Liquidity Wick Filter"
slug: "volume_accelerated_intraday_reversal_with_liquidity_wick_filter_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($close,1) / (Power($high-$low,0.5)+1e-6))  If(Rank($volume/Ref($volume,1))>0.8, -1, 1)  Sign(Mean($close,3)-$close…"
updated: "2026-04-11T20:46:57.758445"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta($close,1) / (Power($high-$low,0.5)+1e-6)) * If(Rank($volume/Ref($volume,1))>0.8, -1, 1) * Sign(Mean($close,3)-$close) ) goes long (short) stocks whose 1-day return is large relative to intraday wick size, only when concurrent volume ranks in top 20 % of universe and price is below its 3-day mean, expecting that high-volume wicks in lagging names quickly revert as aggressive orders exhaust.
**Rationale**: High intraday wicks accompanied by volume spikes indicate aggressive but ultimately absorbed order-flow—often stop-runs or short-covering bursts. When this happens while the stock sits below a short-term mean, the liquidity event is more likely temporary, creating 1-day mean-reversion as micro-structure imbalances normalize. Cross-sectional rank neutralizes broad market moves, focusing on relative liquidity extremes.
**Implementation (Qlib)**: `Rank(Multiply(Add(Multiply(Divide(Delta($close,1),Add(Sqrt(Subtract($high,$low)),0.000001)),If(Greater(Rank(Divide($volume,Ref($volume,1))),0.8),-1,1)),Multiply(Divide(Delta($close,1),Add(Sqrt(Subtract($high,$low)),0.000001)),If(LessEqual(Rank(Divide($volume,Ref($volume,1))),0.8),1,1))),Sign(Subtract(Mean($close,3),$close))))`
**Math Formula**: \text{Rank}\left( \frac{\Delta C_t}{\sqrt{H_t-L_t}+10^{-6}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\frac{V_t}{V_{t-1}}\right)>0.8\right\}}\cdot(-1) + \frac{\Delta C_t}{\sqrt{H_t-L_t}+10^{-6}} \cdot \mathbf{1}_{\left\{\text{Rank}\left(\frac{V_t}{V_{t-1}}\right)\le 0.8\right\}}\cdot(+1) \right) \cdot \text{sgn}\left(\frac{C_t+C_{t-1}+C_{t-2}}{3}-C_t\right)
**IC / RankIC**: -0.0109 / -0.0128
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows weak negative IC (-0.0109) and Rank IC (-0.0128), well below 0.02 threshold, with negative Sharpe (-0.71) and deep max drawdown (-29.6%). RRE, PFS, Diversity and LLM Score all zero indicate no risk-adjusted edge, stability or diversification benefit. The complex double-branch structure appears to cancel signal rather than amplify it, and the sign flip on volume ranking may be inverted versus the hypothesis.
**Suggested Improvements**: Simplify expression to single conditional term: keep the wick-adjusted return only when volume rank >0.8 and price < 3-day mean, then rank; remove the additive mirror branch that neutralizes alpha. Consider using next-day return as target to ensure timing aligns. Test alternative wick measures like (close-low)/(high-low) to better capture intraday exhaustion. Shrink volume threshold to top 10 % and shorten mean look-back to 2 days to raise signal freshness.
