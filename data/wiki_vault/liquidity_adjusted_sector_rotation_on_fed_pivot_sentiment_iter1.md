---
title: "Liquidity-Adjusted Sector Rotation on Fed-Pivot Sentiment"
slug: "liquidity_adjusted_sector_rotation_on_fed_pivot_sentiment_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Delta($volume,5) / Delta($volume,20))  Sign(Corr(Rank($close / Ref($close,5)), FedFundsFutChange, 15))  If(Rank($close /…"
updated: "2026-04-13T02:13:40.046361"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Delta($volume,5) / Delta($volume,20)) * Sign(Corr(Rank($close / Ref($close,5)), FedFundsFutChange, 15)) * If(Rank($close / Ref($close,20)) < 0.4, 1, -1) ) goes long (short) stocks whose 5-day volume surge vs 20-day is extreme AND whose 5-day return rank positively (negatively) correlates with concurrent Fed-funds-future repricing, but only if the stock is already in the bottom 40 % of 20-day cross-sectional momentum, expecting that liquidity-driven sector rotation into (out of) laggards accelerates when the market prices a dovish (hawkish) pivot.
**Rationale**: With the Fed signaling a higher-for-longer pause yet swaps pricing 75 bp of cuts inside 12 m, volatility is concentrated in rate-sensitive laggards. Empirical studies show cross-sectional momentum has decayed while volume-confirmed relative value shifts persist. By conditioning on low 20-day rank we isolate oversold names where a volume spike—validated by co-movement with Fed-funds futures—flags institutional re-allocation instead of noise, capturing non-linear reversal-momentum hybrid alpha under the current bear-flattening regime.
**Implementation (Qlib)**: `Rank(Delta($volume,5) / Delta($volume,20) * Sign(Corr(Rank($close / Ref($close,5)), Delta($close,1), 15)) * If(Less(Rank($close / Ref($close,20)),0.4),1,0) - If(Greater(Rank($close / Ref($close,20)),0.4),1,0))`
**Math Formula**: \text{Signal}_{i,t}=\operatorname{Rank}_{t}\left(\frac{\Delta_{5}V_{i,t}}{\Delta_{20}V_{i,t}}\cdot\operatorname{Sign}\left(\operatorname{Corr}_{15}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-5}}\right),\Delta F_{t}\right)\right)\cdot\mathbf{1}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-20}}\right)<0.4\right)-\mathbf{1}\left(\operatorname{Rank}_{t}\left(\frac{C_{i,t}}{C_{i,t-20}}\right)\geq 0.4\right)\right)
**IC / RankIC**: -0.0040 / -0.0030
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows weak negative IC (-0.004) and Rank IC (-0.003), well below 0.02 threshold, indicating no predictive power. High RRE (0.584) and PFS (>0.83) suggest overfitting or data snooping. Diversity (0.862) is good but LLM score (59.92) is mediocre. The Fed-funds-future proxy was replaced with Delta($close,1) in code, breaking the macro hypothesis. Extreme volume surge condition may be too noisy with 5-day window.
**Suggested Improvements**: 1) Restore original FedFundsFutChange variable instead of Delta($close,1) to test the macro pivot hypothesis properly. 2) Increase volume delta window from 5-day to 10-day to reduce noise while maintaining surge detection. 3) Replace hard 40% momentum threshold with continuous scaling (e.g., Rank(momentum)^3) to preserve cross-sectional information. 4) Add sector-neutralization to isolate liquidity effects from sector momentum. 5) Consider using Fed funds futures changes over 3-day window instead of 1-day for smoother pivot detection.
