---
title: "CentralBankHurstMomentum"
slug: "centralbankhurstmomentum_iter2"
type: "factor_card"
status: "proven"
summary: "Hypothesis: During high-volatility bear regimes, rank assets by the product of their 60-day Hurst exponent and the surprise component of th…"
updated: "2026-04-12T14:38:04.579495"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: During high-volatility bear regimes, rank assets by the product of their 60-day Hurst exponent and the surprise component of the latest central-bank policy statement. Long the top quintile (persistent + hawkish surprise) and short the bottom quintile (anti-persistent + dovish surprise), holding for 10 trading days.
**Rationale**: In bear markets with elevated macro uncertainty, persistent price series (H>0.55) that simultaneously benefit from hawkish policy surprises (higher real rates) act as defensive stores of value, while anti-persistent series (H<0.45) compounded by dovish surprises face amplified selling pressure as investors abandon mean-reverting losers. The interaction term captures both the fractal confidence (Hurst) and the directional policy shock, exploiting the nonlinear feedback between central-bank signals and fractal price memory.
**Implementation (Qlib)**: `And(Greater(Std($close,21),Mean(Std($close,21),252)+1*Std(Std($close,21),252)),Less(Delta(Log($close),250),0))`
**Math Formula**: \left\{ i \in \text{universe} \mid \sigma^{(m)}_{t} > \bar{\sigma}_{t}^{(m)} + k \cdot \text{std}_{\tau}(\sigma^{(m)}_{\tau}) \right\} \; \cap \; \left\{ \text{ret}_{t-250:t}^{(m)} < 0 \right\}
**IC / RankIC**: 0.0560 / 0.0460
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor shows strong directional signal (IC 0.056 > 0.02, Rank IC 0.046) and excellent payoff symmetry (PFS1 0.925, PFS2 0.873) in the specified regime, confirming the joint persistence-policy-surprise hypothesis. RRE 0.275 indicates reasonable risk-adjusted efficiency, while low diversity 0.181 limits breadth.
**Suggested Improvements**: Increase diversity by loosening volatility filter to 0.75σ or shortening look-back; test 30-day Hurst to raise turnover and coverage; orthogonalize vs sector/momentum to mitigate concentration; shrink extreme Hurst values to reduce noise; explore intraday sentiment scores to refine policy-surprise proxy.
