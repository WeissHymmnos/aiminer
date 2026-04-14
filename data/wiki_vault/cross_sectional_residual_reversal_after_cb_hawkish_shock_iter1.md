---
title: "Cross-Sectional Residual Reversal After CB Hawkish Shock"
slug: "cross_sectional_residual_reversal_after_cb_hawkish_shock_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank(-1  (Corr(Rank($close/Ref($close,1)), Rank($volume), 5) + 0.5)  (Delta($close,1) / Std($close,20))  If(Rank($vwap/$close)…"
updated: "2026-04-12T07:13:24.749293"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank(-1 * (Corr(Rank($close/Ref($close,1)), Rank($volume), 5) + 0.5) * (Delta($close,1) / Std($close,20)) * If(Rank($vwap/$close) > 0.8, 1, 0) ) goes long (short) stocks whose 5-day rank price-volume correlation is most negative (positive), whose 1-day return is extreme vs 20-day volatility, and whose VWAP premium is in the top quintile, expecting that hawkish CB surprise drains liquidity, causing intraday overreaction to reverse overnight.
**Rationale**: Recent macro news shows major central banks signaling higher-for-longer rates, draining system-wide liquidity. In this regime, volume-confirmed one-day moves become exaggerated; a strongly negative rank price-volume correlation indicates liquidity-taking exhaustion while a high VWAP premium flags late-day retail chasing. Cross-sectionally ranking isolates the most vulnerable microstructures, and the factor bets on subsequent reversal when liquidity premium normalizes.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Multiply(Const(-1),Add(Corr(Rank(Div($close,Ref($close,1))),Rank($volume),5),Const(0.5))),Divide(Delta($close,1),Std($close,20))),Greater(Rank(Div($vwap,$close)),Const(0.8))))`
**Math Formula**: R_{i,t}=\text{Rank}_t\!\left(\,-1\cdot\left[\,\text{RankCorr}_t\!\left(\,\text{Rank}_t\!\left(\frac{P_{i,t}}{P_{i,t-1}}\right),\;\text{Rank}_t(V_{i,t}),\;5\right)+0.5\,\right]\cdot\frac{P_{i,t}-P_{i,t-1}}{\sigma_{i,t}^{(20)}}\cdot\mathbf{1}\!\left\{\text{Rank}_t\!\left(\frac{\text{VWAP}_{i,t}}{P_{i,t}}\right)>0.8\right\}\right)
**IC / RankIC**: -0.0400 / 0.0680
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows mixed signals: IC is negative (-0.04) contradicting the long premise, yet Rank IC is positive (0.068) and above 0.02 threshold; RRE near 1 and high diversity (0.85) indicate robust, uncrowded signal; PFS1≈0.31 and PFS2≈0.49 show mild but not strong decay; LLM score 51.3 is neutral. Overall, the factor is not definitively effective as IC sign flips vs hypothesis, but Rank IC suggests some ordering power.
**Suggested Improvements**: Flip the sign of the correlation term to Rank(Corr(...)) instead of Rank(-1*Corr(...)) to align IC with intended long/short logic; shorten the correlation window from 5 to 3 days to capture faster liquidity events; replace the 0.5 constant with a cross-sectional z-score to reduce arbitrary offset; try exponential decay weighting on volume to emphasize recent trades; test relaxing the VWAP filter to top 40% to increase breadth and reduce conditioning noise; add sector-neutral ranking to mitigate systematic sector skew; verify overnight vs intraday return decomposition to ensure reversal happens overnight as hypothesized.
