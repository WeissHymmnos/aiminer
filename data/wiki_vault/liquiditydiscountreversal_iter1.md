---
title: "LiquidityDiscountReversal"
slug: "liquiditydiscountreversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-$open)/Ref($close,2)  If(Rank($volume/Ref($volume,1))<0.25,-1,1)  If(Rank($close/Ref($close,1))<0.3,1,-1)…"
updated: "2026-04-11T20:46:59.585901"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ref($close,1)-$open)/Ref($close,2) * If(Rank($volume/Ref($volume,1))<0.25,-1,1) * If(Rank($close/Ref($close,1))<0.3,1,-1) ) goes long stocks that gapped down overnight on record-low volume while their 1-day return is in the bottom 30 % of the universe, expecting the liquidity discount to vanish intraday as bargain hunters step in.
**Rationale**: With the Fed signalling higher-for-longer and cross-asset volatility spiking, overnight liquidity evaporates; crowded shorts gap weak names down on air. Because volume ranks in the lowest quartile the move is not validated, and since the stock already under-performed the market yesterday it trades at an exaggerated discount. When the cash session opens, depth returns and the gap quickly fills, producing a 1-day mean-reversion alpha orthogonal to sector moves.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),$open),Ref($close,2)),Sign(Sub(0.25,Rank(Divide($volume,Ref($volume,1)))))),Sign(Sub(Rank(Divide($close,Ref($close,1))),0.3))))`
**Math Formula**: R_{i,t}=\text{Rank}_t\left(\frac{\text{Ref}(C_{i,t},1)-O_{i,t}}{\text{Ref}(C_{i,t},2)}\cdot\text{sgn}\left(0.25-\text{Rank}_t\left(\frac{V_{i,t}}{\text{Ref}(V_{i,t},1)}\right)\right)\cdot\text{sgn}\left(\text{Rank}_t\left(\frac{C_{i,t}}{\text{Ref}(C_{i,t},1)}\right)-0.3\right)\right)
**IC / RankIC**: 0.0000 / 0.0000
**Effectiveness**: ❌ FAILED
**Review Summary**: All metrics are exactly zero, indicating the factor produces no predictive signal; the complex triple-rank construction collapses to a constant or near-constant value across the universe, so no meaningful long-short spread is generated.
**Suggested Improvements**: 1) Replace nested Rank() with z-score or percentile normalization to preserve cross-sectional dispersion. 2) Split the logic: first screen for gap-downs > xσ, record-low volume flag (e.g., volume < 10th percentile over 20 days), and 1-day return < 30th percentile, then combine with a simple additive or multiplicative weight instead of cascading Sign(Rank()) calls. 3) Add a liquidity filter (dollar-volume > median) to avoid micro-caps that never mean-revert. 4) Introduce a mild intraday momentum term (e.g., 30-min reversal) to confirm bargain-hunter entry before taking position. 5) Retest with decay IC and horizon analysis to verify mean-reversion occurs within 1-5 days.
