---
title: "Volume-Accelerated Cross-Sectional Reversal"
slug: "volume_accelerated_cross_sectional_reversal_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( If(Corr(Rank($volume),Rank($close/Ref($close,1)),3) < -0.4, -1, 1)  (Mean($volume,3)/Mean($volume,15)-1)  TsRank($close-M…"
updated: "2026-04-11T20:50:29.482110"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( If(Corr(Rank($volume),Rank($close/Ref($close,1)),3) < -0.4, -1, 1) * (Mean($volume,3)/Mean($volume,15)-1) * Ts_Rank($close-Mean($close,10),5) ) goes long (short) stocks whose 3-day rank price-volume correlation is strongly negative (positive) and whose 3-day volume surges vs 15-day, expecting that volume-confirmed exhaustion in a high-vol bearish regime triggers sharp cross-sectional reversals.
**Rationale**: Macro: BoJ hawkish shift + sticky US inflation keep global yields elevated, equity risk premium compresses and volatility lifts → investors dump crowded winners, amplifying volume spikes on down-days.  Regime: High-vol bearish → intraday moves over-extend, short-covering rallies fast but selective.  Alpha insight: Kakushadze Alpha-12 shows Sign(Delta($volume))*(-Delta($close)) profits when volume and price move opposite; cross-sectional paper shows relative (not TS) momentum survives.  Orthogonalization note: prior failures combined Hurst filters that collapsed signal; instead use a direct, conditional correlation gate (|ρ|<-0.4) plus volume acceleration to isolate exhausted reversals without noisy regime proxies.  Interaction of rank volume surge and 5-day relative price rank captures imminent snap-backs while staying market-neutral.
**Implementation (Qlib)**: `Rank(If(Less(Corr(CSRank($volume), CSRank($close / Ref($close, 1)), 3), -0.4), -1, 1) * (Mean($volume, 3) / Mean($volume, 15) - 1) * Ts_Rank($close - Mean($close, 10), 5))`
**Math Formula**: \text{Signal}_i = \text{Rank}\left[ \; \mathbf{1}\!\left\{\text{Corr}_{t,3}\!\left(\text{Rank}(V_i),\;\text{Rank}\!\left(\frac{C_i}{C_{i,t-1}}\right)\right) < -0.4\right\} \cdot (-1) \;+\; \mathbf{1}\!\left\{\text{Corr}_{t,3}\!\left(\text{Rank}(V_i),\;\text{Rank}\!\left(\frac{C_i}{C_{i,t-1}}\right)\right) \geq -0.4\right\} \cdot 1 \;\right] \;\times\; \left(\frac{\frac{1}{3}\sum_{k=0}^{2}V_{i,t-k}}{\frac{1}{15}\sum_{k=0}^{14}V_{i,t-k}} - 1\right) \;\times\; \text{TS-Rank}_{t,5}\!\left(C_i - \frac{1}{10}\sum_{k=0}^{9}C_{i,t-k}\right)
**IC / RankIC**: 0.0028 / -0.0144
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor IC 0.0028 is far below 0.02 threshold and Rank IC is slightly negative, indicating no predictive power; RRE=1.0 shows no decay but all other metrics (PFS, Diversity, LLM) are zero, confirming no alpha signal. Volume-price correlation filter appears too strict (-0.4) and the triple interaction dilutes signal.
**Suggested Improvements**: Relax correlation threshold to -0.2 and test asymmetric cuts; replace binary If() with smooth sigmoid weighting; isolate volume surge component by testing it standalone first; shorten Ts_Rank look-back to 3 days; add sector-neutral ranking and market-regime filter (e.g., VIX>20) to focus on exhaustion reversals; finally run step-wise orthogonalization against momentum and liquidity factors to reduce noise.
