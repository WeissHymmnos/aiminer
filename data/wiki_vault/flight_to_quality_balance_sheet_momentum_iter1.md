---
title: "Flight-to-Quality Balance-Sheet Momentum"
slug: "flight_to_quality_balance_sheet_momentum_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( (CashAndShortTermInvestmentsQ/MarketCap) * (1/Max(0.01,TotalDebtQ/MarketCap)) * Ts_Zscore(ROC(Close,20),60) ) rewards large-caps whose balance sheets car…"
updated: "2026-04-14T12:15:02"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0014
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( (CashAndShortTermInvestmentsQ/MarketCap) * (1/Max(0.01,TotalDebtQ/MarketCap)) * Ts_Zscore(ROC(Close,20),60) ) rewards large-caps whose balance sheets carry the highest cash-to-price and lowest debt-to-price ratios while still exhibiting positive 20-day price momentum that is subdued relative to its own 60-day history, capturing the continuous preference for financially resilient yet not overbought names during macro uncertainty.

**Rationale**: April CPI ticked up, 2-yr swap vol >80 %-ile and IG credit spreads widening; investors are rotating away from levered cyclicals toward cash-rich balance-sheet compounders but are wary of names that have already sprinted too far. The cross-sectional rank ensures the signal varies smoothly across the whole universe: high cash, low debt, and momentum that is positive but not extreme scores best. The double balance-sheet ratios discount both default and refinancing risk, while the z-scored momentum prevents buying euphoric highs, a pitfall that killed prior pure-quality factors in 2022.

**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide($close, $close), Divide(1, Max(0.01, Divide($close, $close)))), CSZScore(Delta($close, 20))))`

**Math Formula**: R_i = \text{rank}_i\left(\frac{C_i}{M_i} \cdot \frac{1}{\max\!\bigl(0.01,\,D_i/M_i\bigr)} \cdot z\bigl(r_{i,20},\,60\bigr)\right)

**IC / RankIC**: 0.0014 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC 0.0014 and Rank IC 0.0 are far below the 0.02 threshold; RRE 0.0 confirms no predictive power. The implemented code is tautological (Close/Close = 1) and omits all balance-sheet variables (Cash, Debt, MarketCap) as well as the 60-day z-score window, so the signal is just noise. Sharpe 0.21 and MD -17 % reflect a random long-short rather than a valid factor.

**Suggested Improvements**: Rewrite the expression to actually use balance-sheet data: Rank( (CashAndShortTermInvestmentsQ / MarketCap) * (1 / Max(0.01, TotalDebtQ / MarketCap)) * CSZScore(ROC(Close,20),60) ); ensure quarterly fundamentals are point-in-time aligned to market-cap at signal date; winsorize all ratios at 1 %/99 % to curb outliers; test sector-neutral version to verify the financial-strength effect is not just a sector bet; require IC > 0.02 over at least 5 years of out-of-sample data before deployment.
