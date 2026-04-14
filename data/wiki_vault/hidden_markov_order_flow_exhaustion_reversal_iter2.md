---
title: "Hidden-Markov Order-Flow Exhaustion Reversal"
slug: "hidden_markov_order_flow_exhaustion_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Among stocks whose 3-day hidden-Markov regime probability of ‘High-Volume-Pressure’ drops below 30 % while their 1-day closing strength ((Close-Low)/(High-Low)…"
updated: "2026-04-13T20:11:55"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.106
rank_ic: -0.006
iteration: 2
is_effective: false
simulated: true
---

**Hypothesis**: Among stocks whose 3-day hidden-Markov regime probability of ‘High-Volume-Pressure’ drops below 30 % while their 1-day closing strength ((Close-Low)/(High-Low)) stays above 0.7, next-day return reverses; factor = Rank(CloseStrength) * (-Rank(Delta(RegimeProb_HVP,1))) when RegimeProb_HVP<0.3 else 0.

**Rationale**: PBoC’s steady-rate stance keeps macro volatility suppressed; algos cluster in micro-trend episodes detected by a 2-state HMM on (volume, range, trade size). When the model flips from high-volume-pressure to low-probability but price still closes near the high, late buyers are trapped with evaporating order flow, forcing an overnight unwind that yields next-day mean-reversion. Cross-sectional ranks neutralise market drift while the HMM state change isolates liquidity exhaustion earlier than simple volume deltas.

**Implementation (Qlib)**: `If(Less($close, 0.3), Rank(($close - $low) / ($high - $low)) * (-Rank(Delta($close, 1))), 0)`

**Math Formula**: r_{i,t+1}=\alpha+\beta\cdot f_{i,t}+\epsilon_{i,t}\quad\text{with}\quad f_{i,t}=\begin{cases}\text{Rank}_{c}\left(\frac{C_{i,t}-L_{i,t}}{H_{i,t}-L_{i,t}}\right)\cdot\left(-\text{Rank}_{c}\left(\Delta P_{i,t}^{\text{HVP}}\right)\right)&\text{if }P_{i,t}^{\text{HVP}}<0.3\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.1060 / -0.0060

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong IC (0.106) but negligible Rank IC (-0.006) and low PFS, indicating the rank ordering is noisy; the signal is concentrated in extreme values rather than monotonic across ranks. Diversity is modest (0.161) and RRE 0.094 suggests some alpha beyond risk model. Code incorrectly uses $close instead of RegimeProb_HVP for threshold and delta, so the published factor is not the intended one.

**Suggested Improvements**: Fix code to use RegimeProb_HVP for both threshold and delta: If(Less(RegimeProb_HVP, 0.3), Rank(CloseStrength) * (-Rank(Delta(RegimeProb_HVP, 1))), 0). After correction, verify Rank IC rises above 0.02; if not, try smoothing RegimeProb_HVP with 5-day EMA, winsorize extreme CloseStrength values, and cap the final factor at ±3σ to reduce noise. Consider relaxing the 30 % threshold to 35 % to increase breadth and improve rank monotonicity.
