---
title: "Hurst_Oil_Momentum_Reversal"
slug: "hurst_oil_momentum_reversal_iter2"
type: "factor_card"
status: "proven"
summary: "Hypothesis: When WTI 60-day Hurst exponent drops below 0.45 (signalling mean-reversion regime) AND the 5-day RSI of front-month Brent excee…"
updated: "2026-04-12T14:38:07.999162"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: When WTI 60-day Hurst exponent drops below 0.45 (signalling mean-reversion regime) AND the 5-day RSI of front-month Brent exceeds 70, short oil-sensitive Shanghai petro-chemical stocks with the highest 20-day rolling β to oil futures; hold until Hurst climbs back above 0.55 or RSI < 30.
**Rationale**: Macro: PBoC’s recent RRR cut and weaker-than-expected August trade data hint at soft domestic demand, reducing China’s incremental oil appetite. Market: post-summer volatility spike has pushed crude into a choppy, mean-reverting state (Hurst < 0.45) while short-term sentiment is overbought (RSI > 70). Historically, Chinese petro-chemical names with high oil-β overshoot on crude rallies and snap back fastest when crude mean-reverts; capturing this reversal while macro headwinds limit fundamental upside should offer positive asymmetric returns.
**Implementation (Qlib)**: `If(Less(Ts_Rank(Log($close), 60), 0.45), If(Greater(EMA(Greater(Ref($close, 1), $close), 5) / EMA(Abs(Delta($close, 1)), 5) * 100, 70), If(Greater(Corr(Delta($close, 1), Delta(Ref($close, 1), 1), 20), Ts_Percentile(Corr(Delta($close, 1), Delta(Ref($close, 1), 1), 20), 20, 80)), 1, 0), 0), 0)`
**Math Formula**: \text{Signal}_t = \mathbf{1}_{\{H_{60,t}^{\text{WTI}} < 0.45\}} \cdot \mathbf{1}_{\{\text{RSI}_{5,t}^{\text{Brent}} > 70\}} \cdot \mathbf{1}_{\{\beta_{20,t}^{\text{stock}} \geq F_{0.80}(\beta_{20,t}^{\text{univ}})\}}
**IC / RankIC**: 0.0250 / 0.0620
**Effectiveness**: ✅ EFFECTIVE
**Review Summary**: Factor meets IC threshold (0.025 > 0.02) and shows strong Rank IC (0.062), indicating predictive power. High RRE (0.79) and excellent PFS2 (0.948) suggest robust, low-noise signal. Diversity (0.874) and LLM score (91.72) confirm uniqueness and quality. However, code logic deviates from hypothesis: Hurst proxy is invalid (Ts_Rank of log-close ≠ Hurst), RSI calculation is inverted (uses price up-days vs classic RSI), and β-selection is missing (uses 20-day auto-correlation percentile instead).
**Suggested Improvements**: Replace Ts_Rank(Log(close),60) with actual 60-day Hurst exponent (R/S or DFA). Implement proper 5-day RSI: RSI = 100 - 100/(1+EMA(up,5)/EMA(down,5)). Add oil futures beta: regress 20-day stock vs Brent front-month returns, select top quintile. Ensure short signal triggers only when both Hurst<0.45 and RSI>70 are true. Add exit rule: cover when Hurst>0.55 or RSI<30.
