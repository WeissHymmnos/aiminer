---
title: "Disinflation-Divergence Momentum"
slug: "disinflation_divergence_momentum_iter1"
type: "factor_card"
status: "failed"
summary: "Go long the equal-weight quintile of CSI-300 stocks whose 21-day EMA is above the 63-day EMA, MACD-line > signal-line, and whose latest CPI-sector beta (estima…"
updated: "2026-04-13T19:11:14"
tags: ["You are an expert in momentum and trend-", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.04
rank_ic: 0.031
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Go long the equal-weight quintile of CSI-300 stocks whose 21-day EMA is above the 63-day EMA, MACD-line > signal-line, and whose latest CPI-sector beta (estimated vs urban CPI) has fallen the most YoY; hedge by shorting the inverse quintile. Rebalance weekly.

**Rationale**: Soft-landing pricing power: as headline CPI keeps easing (PBOC easing bias intact) investors reward firms whose inflation-sensitivity is dropping fastest, interpreting the beta compression as margin resilience. Trend filters (EMA & MACD) ensure we only ride names already in technical uptrends, avoiding value traps in a still-uncertain macro backdrop.

**Implementation (Qlib)**: `If(And(Greater(EMA($close,21),EMA($close,63)),Greater(Delta(EMA($close,12),EMA($close,26)),EMA(Delta(EMA($close,12),EMA($close,26)),9))),If(Less(CSRank(Delta(CSRank($close),252)),0.2),$close,0),0) - If(And(Greater(EMA($close,21),EMA($close,63)),Greater(Delta(EMA($close,12),EMA($close,26)),EMA(Delta(EMA($close,12),EMA($close,26)),9))),If(Greater(CSRank(Delta(CSRank($close),252)),0.8),$close,0),0)`

**Math Formula**: R_t = \frac{1}{|L_t|}\sum_{i\in L_t}r_{i,t} - \frac{1}{|S_t|}\sum_{j\in S_t}r_{j,t}
\quad\text{with}\quad
L_t = \left\{i\in\text{CSI300}:\;\text{EMA}_{21}(P_{i,t})>\text{EMA}_{63}(P_{i,t}),\;\text{MACD}_{i,t}>\text{Signal}_{i,t},\;i\in Q_{1,t}^{\beta}\right\}
\quad\text{and}\quad
S_t = \left\{j\in\text{CSI300}:\;\text{EMA}_{21}(P_{j,t})>\text{EMA}_{63}(P_{j,t}),\;\text{MACD}_{j,t}>\text{Signal}_{j,t},\;j\in Q_{5,t}^{\beta}\right\}
\quad\text{where}\quad
Q_{1,t}^{\beta} = \arg\min_{\mathcal{Q}\subset\text{CSI300},|\mathcal{Q}|=60}\Delta\beta_{i,t}^{\text{CPI}},
\quad
Q_{5,t}^{\beta} = \arg\max_{\mathcal{Q}\subset\text{CSI300},|\mathcal{Q}|=60}\Delta\beta_{i,t}^{\text{CPI}}
\quad\text{and}\quad
\Delta\beta_{i,t}^{\text{CPI}} = \beta_{i,t}^{\text{CPI}} - \beta_{i,t-252}^{\text{CPI}}

**IC / RankIC**: -0.0400 / 0.0310

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak predictive power: IC=-0.04 (<0.02) is negative, while Rank IC=0.031 is barely positive; RRE=0.42 indicates moderate robustness, but PFS1=0.94/PFS2=0.09 show unstable hit-rate; Diversity=0.44 is acceptable; LLM score 64.3 suggests code-structure issues. The CPI-beta condition is mis-implemented—code uses 252-day price delta rank instead of CPI-sector beta YoY change—so the intended macro-deflation signal is absent, explaining poor IC.

**Suggested Improvements**: Replace CSRANK(Delta(CSRANK($close),252)) with actual YoY % change of stock-level CPI-sector beta vs urban CPI; confirm sector beta is re-estimated weekly. Lower EMA lookback mismatch: use 21/55 or 25/60 to reduce lag. Add turnover penalty (e.g., signal smoothing with 5-day MA) to cut 0.94 PFS1 instability. Test short-side without EMA/MACD filter to isolate CPI-beta alpha. Require |CPI-beta YoY change| > 1σ before quintile assignment to enhance signal-to-noise.
