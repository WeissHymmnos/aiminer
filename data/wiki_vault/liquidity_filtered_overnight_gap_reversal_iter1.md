---
title: "Liquidity-Filtered Overnight Gap Reversal"
slug: "liquidity_filtered_overnight_gap_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank over the last 5 days revert the next day; factor = sign(ΔCloseOve…"
updated: "2026-04-13T20:11:22"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.033
rank_ic: -0.01
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that gap up overnight (>1.5%) but show contemporaneous shrinkage in dollar-volume rank over the last 5 days revert the next day; factor = sign(ΔCloseOvernight) * Rank(-ΔDVOL_5) * I(|ΔCloseOvernight|>0.015)

**Rationale**: With the central bank on hold and volatility compressed, risk-taking is concentrated in overnight gaps.  When a stock gaps >1.5% on declining 5-day dollar-volume rank, the move is not validated by liquidity; microstructure theory (O’Hara) says such gaps are transient order-flow imbalances rather than informed demand, making next-day mean-reversion likely.  Cross-sectional ranking neutralizes the broad low-vol drift while the 5-day liquidity window avoids the 3-day lookback that previously double-ranked same-direction signals and muted power.

**Implementation (Qlib)**: `If(Greater(Abs(Delta($close,1)),0.015),Sign(Delta($close,1))*Rank(Delta($volume,5)),0)`

**Math Formula**: r_{i,t+1}=\alpha+\beta\cdot\text{sign}(\Delta C_{i,t}^{\text{ON}})\cdot\text{Rank}_{i,t}(-\Delta DVOL_{i,t}^{5})\cdot\mathbb{I}(|\Delta C_{i,t}^{\text{ON}}|>0.015)+\varepsilon_{i,t+1}

**IC / RankIC**: -0.0330 / -0.0100

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is counter-hypothesis: negative IC (-0.033) and weak Rank IC (-0.01) indicate the intended reversals do not occur; high RRE (0.646) shows instability; tiny Diversity (0.004) implies overcrowding; PFS near 0.28 is poor. Factor currently shorts the very stocks that keep rising and vice-versa, so it loses money.

**Suggested Improvements**: Flip the sign to capture true mean-reversion: factor = -sign(ΔCloseOvernight) * Rank(-ΔDVOL_5) * I(|ΔCloseOvernight|>0.015). Replace raw volume with dollar-volume or volume-volatility adjusted measure. Demand shrinkage in volume to be statistically significant (z-score <-1) not just rank. Add sector-neutral rank and cap-scaled rank to reduce overcrowding. Shorten look-back to 3-days or use exponentially-weighted volume change for faster signal. Filter out stocks <5 $ median daily dollar-volume and earnings-announcement days to curb noise. Run decile spread test to verify flipped factor IC>0.02 and Rank IC>0.04 before deployment.
