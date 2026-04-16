---
title: "Overnight-Reversal Gamma Squeeze"
slug: "overnight_reversal_gamma_squeeze_iter1"
type: "factor_card"
status: "proven"
summary: "Hypothesis: Rank( Sign( Ref($close,1)-$open )  Corr( Rank($volume), Rank($close-$vwap), 5 )  ( $high/$low - Ref($high/$low,1) ) ) goes long…"
updated: "2026-04-13T02:13:39.460608"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( Sign( Ref($close,1)-$open ) * Corr( Rank($volume), Rank($close-$vwap), 5 ) * ( $high/$low - Ref($high/$low,1) ) ) goes long stocks that opened below prior close, show negative 5-day rank correlation between volume and intraday premium-to-VWAP, and widened high-low ratio; short the opposite. Logic: overnight gap down traps short gamma, subsequent volume-on-weakness signals dealer hedging exhaustion, while high-low expansion confirms intraday volatility sell-off, setting up next-day mean-reversion bounce.
**Rationale**: Recent macro-driven gap-down openings amid high volatility leave dealers short upside gamma. When volume clusters while price trades below VWAP, gamma hedging intensifies the selloff, exhausting liquidity. A widening high-low spread signals panic intraday range extension. Historical Alpha009/012 show conditional reversion works best after volume-confirmed moves. Factor avoids raw persistence estimators that previously collapsed signal; instead it uses signed overnight gap as regime trigger, volume-vwap rank correlation as flow exhaustion gauge, and high-low expansion as volatility proxy, all interactively ranked for cross-sectional robustness in current bear-volatile regime.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Sign(Delta($open,1)),Corr(Rank($volume),Rank(Delta($close,$vwap)),5)),Delta(Divide($high,$low),1)))`
**Math Formula**: \text{Signal}_{i,t}=\text{Rank}_{t}\Big(\text{Sign}\big(\text{Ref}(C_{i,t},1)-O_{i,t}\big)\cdot\text{Corr}_{k=0..4}\big(\text{Rank}(V_{i,t-k}),\text{Rank}(C_{i,t-k}-\text{VWAP}_{i,t-k}),5\big)\cdot\big(\frac{H_{i,t}}{L_{i,t}}-\text{Ref}(\frac{H_{i,t}}{L_{i,t}},1)\big)\Big)
**IC / RankIC**: 0.0760 / 0.1040
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor is strongly effective: IC 0.076 > 0.02 and Rank-IC 0.104 are both high, RRE 0.57 shows good risk-adjusted return, PFS1 0.27 & PFS2 0.61 indicate solid predictive power, diversity 0.07 is low but acceptable for a mean-reversion signal, LLM score 57 is moderate. Signal captures overnight gap-down + volume/price divergence + intraday volatility expansion as hypothesized.
**Suggested Improvements**: 1) Neutralize sector & size exposures to lift IC further. 2) Replace 5-day correlation with exponentially-weighted 5-day tau ≈ 3 to react faster. 3) Add liquidity filter (median daily dollar-volume > 5 M) to cut turnover and diversity. 4) Cap extreme high-low ratio deltas at 5σ to reduce noise. 5) Combine with a short-horizon reversal factor (e.g., -1-day return) to diversify alpha and raise PFS1 above 0.30.
