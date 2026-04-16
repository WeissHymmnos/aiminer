---
title: "HMM-State-Filtered Liquidity Surge Momentum"
slug: "hmm_state_filtered_liquidity_surge_momentum_iter1"
type: "factor_card"
status: "proven"
summary: "Regime-state probability from a 2-state HMM on overnight gap and first-hour volume predicts next-day return; factor = HMM_state_prob(BullSurge) * Rank(Delta(Vo…"
updated: "2026-04-13T20:11:33"
tags: ["基于隐马尔可夫模型状态识别的市场环境专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.034
rank_ic: 0.013
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Regime-state probability from a 2-state HMM on overnight gap and first-hour volume predicts next-day return; factor = HMM_state_prob(BullSurge) * Rank(Delta(Volume,1)) * Sign(Delta(Close,1)) when overnight gap > 0.5*20-day-ATR.

**Rationale**: Macro backdrop shows central banks on hold, keeping rates steady and suppressing volatility; in this low-vol grind liquidity injections become the dominant price driver. Using a hidden-Markov model trained on overnight return and first-hour volume cleanly separates ‘BullSurge’ from ‘Neutral’ micro-regimes. When the model assigns high probability to BullSurge, a contemporaneous volume spike (Rank(Delta(Volume,1))) aligned with positive prior close change indicates genuine intraday buying pressure rather than the failed ranked-close-strength proxy. The overnight gap filter (>0.5 ATR) ensures we only enter after a macro catalyst, avoiding the double-ranking trap that muted the prior factor. Cross-sectional Rank on volume keeps the signal dollar-neutral and macro-drifts are absorbed by the HMM state probability, making the factor robust to the current cautious-policy environment.

**Implementation (Qlib)**: `If(Greater($open - Ref($close,1), 0.5 * Mean(Abs($high - $low), 20)), Ts_Rank($volume, 20) * Rank(Delta($volume, 1)) * Sign(Delta($close, 1)), 0)`

**Math Formula**: r_{t+1}=\mathbb{1}_{g_t>0.5\cdot\text{ATR}_{20}}\cdot\pi_t(\text{BullSurge})\cdot\text{Rank}\left(\Delta V_t\right)\cdot\text{Sign}(\Delta C_t)

**IC / RankIC**: 0.0340 / 0.0130

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows modest predictive power with IC=0.034 above 0.02 threshold, but Rank IC=0.013 is weak, indicating the factor’s rank ordering is noisy. RRE=0.85 and PFS2=0.75 suggest good stability and low turnover cost, yet PFS1=0.40 implies limited short-term alpha decay. Diversity=0.56 is acceptable. The signal is triggered infrequently (overnight gap > 0.5 ATR) and the HMM regime probability is not explicitly incorporated in the code, creating a mismatch with the hypothesis.

**Suggested Improvements**: 1) Replace the placeholder Ts_Rank($volume,20) with the actual HMM-derived BullSurge regime probability. 2) Standardize the three multiplicative terms (z-score) to prevent any single term from dominating. 3) Relax the gap filter to 0.3 ATR or use a sliding threshold to increase breadth while controlling volatility. 4) Add sector-neutralization or residualization to boost Rank IC. 5) Smooth the final signal with EWMA 3-day to raise PFS1 above 0.5 without materially cutting IC.
