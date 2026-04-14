---
title: "Hurst_Macro_Vol_Momentum"
slug: "hurst_macro_vol_momentum_iter1"
type: "factor_card"
status: "proven"
summary: "Hypothesis: In high-volatility, bear-trending markets, long-short portfolios formed on the interaction between 60-day Hurst exponent and th…"
updated: "2026-04-12T14:37:45.834203"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: In high-volatility, bear-trending markets, long-short portfolios formed on the interaction between 60-day Hurst exponent and the most recent 20-day macro-volatility shock (absolute change in 10-yr CNY swap rate) outperform. Long stocks with both H>0.55 (persistent past losers) and a negative macro-vol shock (rates dropped), short stocks with H<0.45 (mean-reverting past winners) and a positive shock (rates rose).
**Rationale**: When macro volatility spikes, policy easing (falling swap rates) disproportionately benefits firms whose prices have already shown persistent downward trends (H>0.55); investors extrapolate the easing as confirmation of further decline, keeping these names oversold and cheap. Conversely, firms that had mean-reverting strength (H<0.45) are punished when rates rise because their prior rebounds are now viewed as unsustainable in a tightening backdrop. The interaction isolates segments where behavioural extrapolation is strongest, yielding 1- to 3-month reversal gains while staying aligned with current bear-market, high-vol regime.
**Implementation (Qlib)**: `If(And(Greater(Std($close,20),Ts_Percentile(Std($close,20),252,75)),Less(Mean($close,200),Ref(Mean($close,200),1))),If(And(Greater(CSRank($close),0.55),Less(Delta($close,20),0)),1,0)+If(And(Less(CSRank($close),0.45),Greater(Delta($close,20),0)),1,0),0)`
**Math Formula**: R_{i,t\rightarrow t+k}=\alpha+\beta_1 D^{H>0.55}_{i,t}\cdot D^{\Delta r<0}_t+\beta_2 D^{H<0.45}_{i,t}\cdot D^{\Delta r>0}_t+\gamma X_{i,t}+\epsilon_{i,t},\quad\text{with }k\in[21,63],\;\sigma^{mkt}_t>\theta_\sigma,\;\text{trend}_t<0
**IC / RankIC**: 0.0490 / 0.0060
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor shows positive IC (0.049) above 0.02 threshold, but Rank IC (0.006) is very weak, indicating poor ordinal predictive power. RRE near 0.5 and low diversity (0.02) suggest high turnover and concentrated bets. PFS metrics indicate modest but inconsistent profitability. LLM score of 65 is moderate. The factor may capture some alpha but lacks robustness.
**Suggested Improvements**: 1) Replace CSRanks with actual Hurst exponent calculation (e.g., via R/S analysis) instead of proxying with price rank. 2) Use actual 10-yr CNY swap rate data instead of Delta($close,20) as macro-vol shock proxy. 3) Add sector/neutralization to reduce concentration risk. 4) Increase holding period beyond 20 days to lower turnover (current diversity 0.02 implies daily rebalancing). 5) Test asymmetric thresholds (e.g., H>0.6 vs H<0.4) to improve signal-to-noise. 6) Add liquidity filter to ensure tradability of extreme Hurst portfolios.
