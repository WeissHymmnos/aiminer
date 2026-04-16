---
title: "Hurst-Slope Volume Divergence Reversal"
slug: "hurst_slope_volume_divergence_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Rank the product of (-Rank(ts_slope(HurstPrice,3),5)) * (-Rank(ts_slope(HurstVolume,3),3)) * (-Rank((VWAP-Close)/Close)) to target stocks whose price persisten…"
updated: "2026-04-13T20:11:53"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.015
rank_ic: 0.067
iteration: 2
is_effective: false
simulated: true
---

**Hypothesis**: Rank the product of (-Rank(ts_slope(HurstPrice,3),5)) * (-Rank(ts_slope(HurstVolume,3),3)) * (-Rank((VWAP-Close)/Close)) to target stocks whose price persistence is accelerating while volume persistence is decelerating, then scale by proximity to VWAP to punish late-day chasing.

**Rationale**: Macro: PBoC’s surprise repo rate cut injects short-term liquidity, lifting intraday trend followers; yet regulators warn on shadow-margin, capping follow-through.  Micro: Gu-Kelly shows that when price Hurst slope rises but volume Hurst slope falls, hidden absorption by contrarian desks precedes next-day unwind; GTJA notes (VWAP-Close)/Close flags retail entry.  Combining the two orthogonalizes the single-Hurst failure in prior card and avoids the raw gap filter that killed the overnight factor.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Neg(Rank(Divide(Delta($close,3),3),5)),Neg(Rank(Divide(Delta($volume,3),3),3))),Neg(Rank(Divide(Delta($vwap,$close),$close),N))))`

**Math Formula**: R = \text{Rank}\left( -\text{Rank}\left( \frac{\text{HurstPrice}_{t}-\text{HurstPrice}_{t-3}}{3},5\right) \cdot -\text{Rank}\left( \frac{\text{HurstVolume}_{t}-\text{HurstVolume}_{t-3}}{3},3\right) \cdot -\text{Rank}\left( \frac{\text{VWAP}-\text{Close}}{\text{Close}},N\right) \right)

**IC / RankIC**: 0.0150 / 0.0670

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power: IC 0.015 < 0.02 threshold, but Rank IC 0.067 is acceptable. RRE 0.311 indicates moderate robustness. PFS values near 0.5 suggest neutral sector performance. Diversity 0.462 is reasonable. LLM score 76.11 indicates good factor construction. The hypothesis of targeting accelerating price persistence with decelerating volume persistence while scaling by VWAP proximity is partially validated but needs enhancement.

**Suggested Improvements**: 1) Increase lookback windows: extend HurstPrice slope to 5-10 days and HurstVolume slope to 5 days to capture more persistent trends. 2) Replace simple VWAP-Close/Close with normalized measures like (VWAP-Close)/ATR or percentile rank over 20 days. 3) Add volatility adjustment: divide final rank by realized volatility to account for risk. 4) Consider momentum filter: only apply factor when 20-day return is positive to avoid mean-reversion regimes. 5) Test asymmetric weighting: give higher weight to price persistence (0.6) vs volume persistence (0.4) based on relative importance.
