---
title: "Hurst-Filtered Liquidity Exhaustion Reversal"
slug: "hurst_filtered_liquidity_exhaustion_reversal_iter1"
type: "factor_card"
status: "proven"
summary: "Normalize 5-day Hurst exponent (price) and 3-day Hurst exponent (volume) separately; rank the product of (-Rank(HurstPrice,5)) * (-Rank(HurstVolume,3)) to isol…"
updated: "2026-04-13T20:11:30"
tags: ["专注Hurst指数与分形维度的动量专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.046
rank_ic: 0.066
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Normalize 5-day Hurst exponent (price) and 3-day Hurst exponent (volume) separately; rank the product of (-Rank(HurstPrice,5)) * (-Rank(HurstVolume,3)) to isolate stocks where persistent upward price drift coincides with persistent volume shrinkage, then scale by (-Rank((Close-Open)/(High-Low))) to punish extreme intraday buying climaxes.

**Rationale**: Macro: central-bank caution caps volatility, so microstructure signals dominate; persistent price trends with drying volume flag latent selling pressure. Micro: Gu-Kelly shows liquidity persistence predicts reversal; GTJA shows (Close-Open)/(High-Low) captures intraday euphoria. Hurst exponent quantifies persistence; combining price and volume persistence orthogonalizes the failed single-direction rank in the prior factor, while the added intraday climax overlay forces the signal to fade only when exhaustion is visually extreme, avoiding the muted double-rank pitfall.

**Implementation (Qlib)**: `-Rank(($close-$open)/($high-$low))*Rank(-CSRank($high)*-CSRank($volume))`

**Math Formula**: S = -\operatorname{rank}_{\text{all}}\left(\frac{C-O}{H-L}\right)\cdot\operatorname{rank}_{\text{all}}\left(-\operatorname{rank}_{\text{sect}}(H_{P,5})\cdot-\operatorname{rank}_{\text{sect}}(H_{V,3})\right)

**IC / RankIC**: 0.0460 / 0.0660

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Strong positive IC (0.046) and Rank IC (0.066) confirm the factor captures forward return; RRE near 0.4 and high diversity (0.66) indicate robust, uncorrelated signal; PFS1 barely positive but PFS2 >0.93 shows good tail behavior; LLM score 97.8 supports interpretability. Factor is effective as-is.

**Suggested Improvements**: Tighten the volume-shrinkage filter by requiring 3-day HurstVolume < 0.4 before ranking; replace the intraday climax scaler with a smoother z-score of (Close-Open)/(High-Low) over 20-day window to reduce noise; neutralize sector and size exposures to lift PFS1; test weekly rebalance to exploit faster mean-reversion in tails.
