---
title: "Shrinking-Volume Reversal"
slug: "shrinking_volume_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: After two consecutive weeks of below-average volume while price remains above its 20-day MA, next-week CSI-300 return is negati…"
updated: "2026-04-11T20:44:37.400170"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: After two consecutive weeks of below-average volume while price remains above its 20-day MA, next-week CSI-300 return is negatively related to the prior-week return (i.e., winners reverse down, losers snap up).
**Rationale**: Bull trend with weakening momentum + falling volume signals fading buyer conviction; fat-tailed returns show frequent over-reactions. When volume keeps shrinking, late buyers lack support and recent winners become vulnerable to fast profit-taking while beaten-down names attract bottom-fishers, creating a short-term mean-reversion payoff.
**Implementation (Qlib)**: `If(And(Less($volume,Mean(Ref($volume,1),52)),Less($volume,Mean($volume,52)),Greater($close,Mean($close,20))),$close-Ref($close,5),0)`
**Math Formula**: R_{t+1} = \alpha + \beta \, R_t \, I_t + \varepsilon_{t+1}, \quad \beta < 0
**IC / RankIC**: 0.0063 / -0.0013
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor IC 0.0063 and Rank IC –0.0013 are both far below the 0.02 threshold; RRE, PFS, Diversity and LLM Score are zero, indicating no predictive power or portfolio utility. Sharpe is high but driven by extremely sparse positions, not signal strength. Hypothesis of short-term mean-reversion after low-volume consolidation is not validated.
**Suggested Improvements**: Relax the dual 52-week volume filter to increase breadth; replace binary 0/1 signal with z-scored or quintile ranking; test shorter volume look-back (10-20 days) and add momentum/turnover interaction; verify reversal horizon (1-5 days vs 1 week) and include sector/neutralization to raise IC above 0.02.
