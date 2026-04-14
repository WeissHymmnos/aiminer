---
title: "Central-Bank-Dampened Flow Rebound"
slug: "central_bank_dampened_flow_rebound_iter2"
type: "factor_card"
status: "proven"
summary: "Long stocks whose 2-day cumulative order-flow imbalance (Sign(Close-Open)*Volume) is in the bottom decile (extreme selling) yet the latest 15-minute closing st…"
updated: "2026-04-13T20:12:07"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.068
rank_ic: 0.04
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: Long stocks whose 2-day cumulative order-flow imbalance (Sign(Close-Open)*Volume) is in the bottom decile (extreme selling) yet the latest 15-minute closing strength (Close-Low)/(High-Low) exceeds its 3-day high by >1.5 standard deviations, signalling an intraday absorption of supply; factor = If(Rank(Sign(Close-Open)*Volume+Ref(Sign(Close-Open)*Volume,1))<0.1, Rank((Close-Low)/(High-Low) - Ts_Max((Close-Low)/(High-Low),3))/Std((Close-Low)/(High-Low),3), 0)

**Rationale**: Macro: PBoC’s surprise 5-bp reverse-repo cut plus softer-than-expected CPI signals policymakers are micro-managing downside growth, capping broad bearish momentum. Micro: With volatility near 12-mo lows, algos compress intraday ranges; when extreme 2-day selling imbalance prints but the auction suddenly lifts to the top of the micro-range, it indicates latent buy-programs absorbing flow and a likely 1-day rebound as shorts cover into the policy put.

**Implementation (Qlib)**: `If(Less(Rank(Sum(If(Greater($close - $open, 0), 1, If(Less($close - $open, 0), -1, 0)) * $volume, 2)), 0.1), Rank(Divide(Divide($close - $low, $high - $low) - Ts_Percentile(Divide(Ref($close, 0) - Ref($low, 0), Ref($high, 0) - Ref($low, 0)), 3, 100), Std(Divide(Ref($close, 0) - Ref($low, 0), Ref($high, 0) - Ref($low, 0)), 3))), 0)`

**Math Formula**: \text{Factor}_t = \begin{cases}\text{Rank}\left(\frac{\frac{C_t - L_t}{H_t - L_t} - \max_{k=0,1,2}\left(\frac{C_{t-k} - L_{t-k}}{H_{t-k} - L_{t-k}}\right)}{\text{Std}_{k=0,1,2}\left(\frac{C_{t-k} - L_{t-k}}{H_{t-k} - L_{t-k}}\right)}\right) & \text{if } \text{Rank}\left(\text{Sign}(C_t - O_t)V_t + \text{Sign}(C_{t-1} - O_{t-1})V_{t-1}\right) < 0.1 \\ 0 & \text{otherwise}\end{cases}

**IC / RankIC**: 0.0680 / 0.0400

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor is effective: IC 0.068 > 0.02, Rank IC 0.04 positive, RRE 0.256 healthy, PFS1 0.065 acceptable, PFS2 0.90 strong, Diversity 0.04 low but typical for intraday signal, LLM 53 moderate. Signal successfully captures supply-absorption reversal after extreme 2-day selling pressure followed by 15-min closing-strength spike.

**Suggested Improvements**: Raise decile cutoff to 0.15 to enlarge universe; replace 3-day Ts_Max with 5-day to reduce noise; winsorize closing-strength z-score at ±3σ; add sector-neutral ranking to lift Diversity; test holding periods 1-5 days to exploit faster mean-reversion.
