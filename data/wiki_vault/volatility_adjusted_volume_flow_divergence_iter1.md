---
title: "Volatility-Adjusted Volume Flow Divergence"
slug: "volatility_adjusted_volume_flow_divergence_iter1"
type: "factor_card"
status: "proven"
summary: "Rank( Ts_Zscore( Delta($volume,1) / (Std($close,5) + 1e-6), 20 ) * Sign( Corr($close, $volume, 5) - Ref(Corr($close, $volume, 20),5) ) )"
updated: "2026-04-14T12:32:49"
tags: ["利用高频量价相关性挖掘的量价专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.034
rank_ic: 0.099
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Rank( Ts_Zscore( Delta($volume,1) / (Std($close,5) + 1e-6), 20 ) * Sign( Corr($close, $volume, 5) - Ref(Corr($close, $volume, 20),5) ) )

**Rationale**: Macro: With the Fed on an extended pause and real rates still positive, liquidity is scarce; moves that occur on outsized volume relative to recent volatility yet show a deteriorating close-volume correlation are likely driven by impatient liquidity takers and should mean-revert. Market regime is high-vol/bearish, so micro-structure reversals dominate. Cross-agent lesson: raw volume deltas fail (IC<0.01) because they ignore volatility regime; normalising by 5-day close std keeps the measure stationary, while the sign term captures the slope of the liquidity correlation curve—when 5-day correlation drops below where it was 5 days ago, the order flow is losing sponsorship. Rank ensures a smooth cross-sectional continuum, avoiding binary flags.

**Implementation (Qlib)**: `Rank(Mul(Div(Sub(Div(Delta($volume,1),Add(Std($close,5),0.000001)),Mean(Div(Delta($volume,1),Add(Std($close,5),0.000001)),20)),Std(Div(Delta($volume,1),Add(Std($close,5),0.000001)),20)),Sign(Sub(Corr($close,$volume,5),Corr(Ref($close,5),Ref($volume,5),20)))))`

**Math Formula**: \text{Rank}_{t}\left(\frac{\frac{V_{t}-V_{t-1}}{\sigma_{C,5,t}+10^{-6}}-\mu_{Z,20}}{\sigma_{Z,20}}\cdot\text{sign}\left(\rho_{CV,5,t}-\rho_{CV,20,t-5}\right)\right)

**IC / RankIC**: 0.0340 / 0.0990

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.034 and Rank IC 0.099, both above 0.02 threshold. RRE 0.805 indicates good stability. PFS metrics suggest moderate turnover. Diversity 0.56 is acceptable. LLM score 63.92 confirms reasonable complexity. Factor effectively captures volume shock normalized by recent volatility, adjusted for sign of correlation change between price and volume.

**Suggested Improvements**: Consider shortening z-score window from 20 to 10-15 days to reduce turnover and improve PFS. Test replacing Std($close,5) with ATR or volume-weighted volatility. Evaluate if Sign() term could be replaced with smooth transition function to reduce noise. Try capping extreme z-score values at +/-3 to mitigate outliers. Consider adding sector-neutral ranking to improve robustness.
