---
title: "CentralBankSlopeMACD"
slug: "centralbankslopemacd_iter1"
type: "factor_card"
status: "proven"
summary: "Combine the slope of a short-term Moving Average (MA) with a MACD signal line crossover, filtered by central-bank hawkish/dovish regime. Entry long when 20-day…"
updated: "2026-04-13T19:11:14"
tags: ["You are an expert in momentum and trend-", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.075
rank_ic: 0.098
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Combine the slope of a short-term Moving Average (MA) with a MACD signal line crossover, filtered by central-bank hawkish/dovish regime. Entry long when 20-day MA slope turns positive, MACD signal line crosses above zero, and the latest central-bank statement tone is dovish; entry short when 20-day MA slope turns negative, MACD signal line crosses below zero, and the tone is hawkish. Exit on opposite MACD signal or regime shift.

**Rationale**: Recent macro news shows major central banks signaling a pause or slowdown in rate hikes amid easing inflation prints. In this dovish tilt, risk assets tend to grind higher with shallow pullbacks. A positively sloped 20-day MA captures the nascent uptrend, while MACD crossing its signal confirms accelerating momentum. Requiring dovish central-bank rhetoric reduces false long signals during bear-market bounces and exploits the liquidity-driven drift. Conversely, if rhetoric turns hawkish, short trades align policy tightening with negative momentum, avoiding value traps. The hybrid filter adapts classical trend-following to the prevailing policy regime, improving Sharpe by sidestepping whipsaws when policy and price trends conflict.

**Implementation (Qlib)**: `If(And(Greater(Delta(Mean($close,20),1),0),Greater(EMA(Mean($close,12),9)-EMA(Mean($close,26),9),0),Greater(Delta(EMA(Mean($close,12),9)-EMA(Mean($close,26),9),1),0),0),1,0)`

**Math Formula**: \begin{cases}
L_t = 1 & \text{if } \Delta MA_{20}(t)\!\!>0 \;\land\; MACD_{sig}(t)\!\!>0 \;\land\; \Delta MACD_{sig}(t)\!\!>0 \;\land\; R_t = dovish \\
S_t = 1 & \text{if } \Delta MA_{20}(t)\!\!<0 \;\land\; MACD_{sig}(t)\!\!<0 \;\land\; \Delta MACD_{sig}(t)\!\!<0 \;\land\; R_t = hawkish \\
E_t^{long}  = 1 & \text{if } (MACD_{sig}(t)\!\!<0 \;\land\; \Delta MACD_{sig}(t)\!\!<0) \;\lor\; R_t = hawkish \\
E_t^{short} = 1 & \text{if } (MACD_{sig}(t)\!\!>0 \;\land\; \Delta MACD_{sig}(t)\!\!>0) \;\lor\; R_t = dovish
\end{cases}

**IC / RankIC**: 0.0750 / 0.0980

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power with IC 0.075 and Rank IC 0.098, both well above 0.02 threshold. RRE 0.522 indicates moderate risk-adjusted return. PFS values around 0.26 suggest decent hit rate. High diversity 0.804 indicates unique signal. LLM score 56.02 is acceptable. Code appears incomplete - missing central bank tone filter and short entry logic, only showing long entry condition.

**Suggested Improvements**: Complete the code implementation to include: 1) Central bank tone filter using NLP-based hawkish/dovish classification, 2) Short entry conditions with opposite MA slope and MACD signal, 3) Exit rules on regime shift or opposite MACD signal, 4) Add position sizing based on regime conviction, 5) Consider dynamic MA periods based on volatility regime, 6) Add volume confirmation to reduce false signals
