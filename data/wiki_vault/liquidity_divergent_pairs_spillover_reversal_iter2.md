---
title: "Liquidity-Divergent Pairs Spillover Reversal"
slug: "liquidity_divergent_pairs_spillover_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Among sector-neutral pairs pre-selected by 20-day cointegration, the leg whose intraday VWAP momentum diverges most negatively from its 5-day liquidity rank (i…"
updated: "2026-04-13T20:12:11"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.0012
rank_ic: 0.0133
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Among sector-neutral pairs pre-selected by 20-day cointegration, the leg whose intraday VWAP momentum diverges most negatively from its 5-day liquidity rank (i.e. VWAP up, volume rank down) will revert next day; factor = Rank(Delta(VWAP,1)) * (-Rank(Delta(Volume,5))) applied only to the cointegrated pair member with the higher 1-day VWAP change, scaled by pair z-score distance.

**Rationale**: PBoC keeps 1-yr LPR unchanged while export data surprises to the downside—macro stalemate compresses cross-sectional volatility and drives capital into mean-reverting pairs. GTJA shows VWAP better captures intraday smart-money pressure than close-price, and Gu-Kelly finds liquidity contraction is the strongest non-linear reversal cue. By restricting the signal to cointegrated peers we exploit temporary liquidity-induced divergences rather than idiosyncratic noise, avoiding the volume-only gaps that failed in three prior agents. Cross-sectional ranks neutralize the broad grind, while the error-correction framework keeps net dollar exposure near zero—ideal for the current low-vol, policy-on-hold regime.

**Implementation (Qlib)**: `If(And(Greater(Delta($vwap,1),0),Greater(Delta(Ref($vwap,1),1),0)),Rank(Delta($vwap,1)),0) * (-Rank(Delta(Ts_Rank($volume,5),5))) / Abs(CSRank($close))`

**Math Formula**: F_{i,t}=\frac{1}{z_{p,t}}\cdot\mathbb{1}_{i=\arg\max_{j\in p}\Delta\text{VWAP}_{j,t}}\cdot\text{Rank}_{\mathcal{S}_t}\bigl(\Delta\text{VWAP}_{i,t}\bigr)\cdot\Bigl(-\text{Rank}_{\mathcal{S}_t}\bigl(\Delta\text{Vol}_{i,t}^{(5)}\bigr)\Bigr)

**IC / RankIC**: -0.0012 / 0.0133

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor IC is negative and far below 0.02 threshold; Rank IC is only 0.0133, indicating weak predictive power. RRE, PFS, Diversity and LLM Score all zero; Sharpe negative and max drawdown -34%. The divergence signal is not capturing next-day mean-reversion in the cointegrated universe.

**Suggested Improvements**: 1) Replace 1-day VWAP delta with intraday momentum measured from open-to-VWAP to avoid overnight gap noise. 2) Use residual momentum (VWAP beta-adjusted to sector ETF) instead of raw rank to sharpen divergence. 3) Condition entry on pair z-score >1.5 and overnight spread gap <0.3σ to ensure dislocation is fresh and tradable. 4) Scale position by 20-day intraday volatility rather than price rank to equalize risk. 5) Add liquidity filter (ADV >50M) and cancel if either leg’s 5-day volume rank is outside top-80% to reduce slippage. 6) Smooth volume rank with exponential decay (half-life 5 days) to dampen noisy volume spikes. 7) Run separate regressions per GICS sector to allow sector-specific mean-reversion speeds. 8) Combine with short-term reversal alpha (close-to-close return) in a sector-neutral composite to lift IC above 0.02.
