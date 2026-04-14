---
title: "Overnight-Reversal-On-Trade-War-Headlines"
slug: "overnight_reversal_on_trade_war_headlines_iter1"
type: "factor_card"
status: "failed"
summary: "After 21:00 UTC when headlines cross about renewed US-China trade-war tariffs, equities that drop >2 % in the overnight session revert the next cash day if the…"
updated: "2026-04-13T19:11:10"
tags: ["You are an expert in mean-reversion trad", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.042
rank_ic: 0.137
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: After 21:00 UTC when headlines cross about renewed US-China trade-war tariffs, equities that drop >2 % in the overnight session revert the next cash day if the headline is not followed by concrete policy within 8 hours. Go long at the open with a 1-day holding period, targeting a +0.8 % mean-reversion while capping downside at −0.9 %.

**Rationale**: In the current high-volatility bearish regime, investors over-discount overnight tweets or unsourced leaks about tariffs because they hedge with index puts that are already expensive. Once the Asian and European sessions fail to produce an official announcement, the gamma squeeze eases and the drift from systematic re-balancing flows dominates, pushing the price back toward the prior day’s close. This overnight headline premium is transient and mean-reverts intraday, providing a short-term edge before macro uncertainty is resolved.

**Implementation (Qlib)**: `If(And(Less(Delta($open,1)/Ref($close,1),-0.02), Ref($volume,1)==1, Ref($volume,8)==0), 0.008, If(And(Less(Delta($open,1)/Ref($close,1),-0.02), Ref($volume,1)==1, Ref($volume,8)==0), -0.009, 0))`

**Math Formula**: R_{i,t+1}=\begin{cases}+0.8\% & \text{if } r_{i,t}^{\text{overnight}}<-2\%,\ H_t=1,\ P_{t+8}=0,\ \text{entry at open, exit at close}\\ -0.9\% & \text{if } r_{i,t}^{\text{overnight}}<-2\%,\ H_t=1,\ P_{t+8}=0,\ \text{stop-loss hit}\\ 0 & \text{otherwise}\end{cases}

**IC / RankIC**: -0.0420 / 0.1370

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC is negative (-0.042) and far below 0.02 threshold, contradicting the expected positive mean-reversion; Rank IC is modest (0.137) but not sufficient to offset the negative IC. RRE and PFS1 are high, indicating good risk-adjusted return and hit-rate, yet the negative IC signals the factor is betting against itself. Diversity is acceptable (0.64) and LLM score is strong (72), but the core signal is inverted.

**Suggested Improvements**: Flip the sign of the signal to go short instead of long; tighten the overnight drop filter to >3 % to reduce noise; require headline volume spike (>2σ) within 1 hour of 21:00 UTC to confirm tariff headline; add policy-announcement NLP flag within 8h window to ensure no concrete action; introduce sector-neutralization to avoid single-sector bias; test 2-day holding to capture slower reversion; cap position size at 1 % to control tail risk.
