---
title: "Liquidity-Adjusted Overnight Gap Reversal"
slug: "liquidity_adjusted_overnight_gap_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1)-Ref($open,1)) / Ref($close,2)  (1 / (1+Rank($volume/Ref($volume,1))))  Sign(Mean($close,5)-$close) ) goes…"
updated: "2026-04-13T02:13:36.889569"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ref($close,1)-Ref($open,1)) / Ref($close,2) * (1 / (1+Rank($volume/Ref($volume,1)))) * Sign(Mean($close,5)-$close) ) goes long (short) stocks whose overnight gap is large vs prior close, scaled inversely by the concurrent volume spike rank, and only when the stock is below its 5-day mean price, expecting that low-liquidity overnight gaps in temporarily oversold names revert within 1 day as liquidity normalizes.
**Rationale**: Macro: With central banks on hold and inflation sticky, micro-price discovery dominates; overnight gaps often reflect stale quotes rather than fresh information, especially when volume is thin. Market regime: High intraday volatility and bearish sentiment increase probability of liquidity gaps at open. Microstructure: Low volume gap-days indicate constrained price discovery; coupling the gap size with an inverse liquidity scaler and a short-term mean-reversion flag (price below 5-day mean) isolates gaps most likely to fade as volume returns, avoiding the failed pure-mean-reversion structures of past agents while retaining their overnight-gap insight.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Delta(Ref($close,1),Ref($open,1)),Ref($close,2)),Divide(1,Add(1,Rank(Divide($volume,Ref($volume,1)))))),Sign(Delta(Mean($close,5),$close))))`
**Math Formula**: \text{Signal}_t = \text{Rank}\left( \frac{\text{Ref}(C_t,1) - \text{Ref}(O_t,1)}{\text{Ref}(C_t,2)} \cdot \frac{1}{1 + \text{Rank}\left(\frac{V_t}{\text{Ref}(V_t,1)}\right)} \cdot \text{Sign}\left(\frac{1}{5}\sum_{i=0}^{4} \text{Ref}(C_t,i) - C_t\right) \right)
**IC / RankIC**: -0.0400 / 0.1270
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows strong rank IC (0.127) but negative IC (-0.04), indicating the rank ordering works yet raw predictions are inverted. High RRE (0.834) suggests overfitting; low diversity (0.173) implies crowdedness. PFS1 > PFS2 shows short-horizon decay. Sign reversal likely stems from the Sign(Mean($close,5)-$close) term flipping intended long/short logic.
**Suggested Improvements**: Invert the Sign term to Sign($close-Mean($close,5)) to align with oversold-reversion hypothesis; shrink extreme volume-spike weights via capped inverse rank; replace 5-day mean with 5-day EWMA or add z-score standardization; introduce sector/market neutralization and liquidity filter (e.g., $volume > 20-day median) to reduce crowdedness; shorten look-back windows and apply L1 regularization to lower RRE.
