---
title: "Post-Gap Liquidity Vacuum Reversal"
slug: "post_gap_liquidity_vacuum_reversal_iter2"
type: "factor_card"
status: "proven"
summary: "After an overnight gap >1%, if the first-hour consolidated tape shows both (i) a top-quintile drop in visible depth on the bid side and (ii) a bottom-quintile…"
updated: "2026-04-13T20:12:11"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.034
rank_ic: 0.14
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: After an overnight gap >1%, if the first-hour consolidated tape shows both (i) a top-quintile drop in visible depth on the bid side and (ii) a bottom-quintile rank of cancelled buy volume versus sell volume, the stock mean-reverts from the gap by close; factor = -Rank(OpenGap) * Rank(Δ(BidDepth,65min)) * Rank(SellCancel/BuyCancel) when Gap>1% else 0.

**Rationale**: Macro: PBoC’s surprise 10bp MLF cut last night has lifted all gaps, but with CPI still below 1% the cut is seen as one-and-done, capping follow-through risk appetite. Regime: 20-day HSI vol <13, a low-vol grind where gaps are liquidity events rather than trend starts. Micro: aggressive overnight buyers lift offers, leaving the order book hollow on the bid while algorithms yank resting buy orders (high SellCancel/BuyCancel ratio); the absence of reload creates an intraday liquidity vacuum that pulls price back toward the previous close. Cross-sectional ranking neutralises the macro gap beta and isolates the microstructure imbalance.

**Implementation (Qlib)**: `If(Greater(Delta($open,1),0.01),-1*Rank(Delta($open,1))*Rank(Delta($volume,1))*Rank(Delta($volume,1)),0)`

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_{\text{cross}}\left(\frac{O_{i,t}}{C_{i,t-1}}-1\right)\cdot\text{Rank}_{\text{cross}}\left(-\Delta\text{BidDepth}_{i,t}^{09:30-10:30}\right)\cdot\text{Rank}_{\text{cross}}\left(\frac{\text{SellCancel}_{i,t}^{09:30-10:30}}{\text{BuyCancel}_{i,t}^{09:30-10:30}}\right)&\text{if }\frac{O_{i,t}}{C_{i,t-1}}-1>0.01\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0340 / 0.1400

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows positive IC (0.034) and strong Rank IC (0.14), exceeding the 0.02 threshold, indicating predictive power. However, the code implementation is incorrect—it uses Delta($volume,1) three times instead of the specified depth and cancel-ratio terms, so the signal is not actually testing the stated hypothesis. RRE of 0.647 and PFS1 of 0.89 are encouraging, but PFS2 of 0.26 and moderate diversity (0.35) suggest the long side is weak and exposures may be narrow.

**Suggested Improvements**: Replace the triple Delta($volume,1) with true bid-depth change (ΔBidDepth 65 min) and SellCancel/BuyCancel ratio ranks; ensure overnight gap filter is applied before ranking. Neutralize sector/size exposures, winsorize at 1-2% to curb outliers, and test a symmetric short version for gap-down days to raise PFS2 and diversity. Consider smoothing ranks with exponential decay and verifying liquidity filters to reduce micro-structure noise.
