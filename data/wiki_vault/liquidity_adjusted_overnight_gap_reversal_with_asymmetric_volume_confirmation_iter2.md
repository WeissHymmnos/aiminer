---
title: "Liquidity-Adjusted Overnight Gap Reversal with Asymmetric Volume Confirmation"
slug: "liquidity_adjusted_overnight_gap_reversal_with_asymmetric_volume_confirmation_iter2"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up >0.5% overnight on a day when their cancelled-order ratio (cancelled/shares-traded) spikes above its 5-day 80th-percentile band, but the fol…"
updated: "2026-04-13T20:12:11"
tags: ["基于协整关系与误差修正模型的统计套利专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.026
rank_ic: 0.008
iteration: 2
is_effective: false
simulated: true
---

**Hypothesis**: Stocks that gap up >0.5% overnight on a day when their cancelled-order ratio (cancelled/shares-traded) spikes above its 5-day 80th-percentile band, but the following 30-min volume is below its 5-day median, reverse intraday; factor = -Rank(OpenGap) * Rank(Delta(CancelRatio,5)) * If(T0_30min_Volume<Median(T0_30min_Volume,5),1,0) when OpenGap>0.5%, else 0.

**Rationale**: With the PBoC on hold and CPI nudging 3.1%, policy uncertainty compresses intraday ranges; algorithms chase thin overnight gaps. A gap >0.5% coinciding with a 5-day high cancel ratio flags stale aggressive bids, while the subsequent 30-min volume shortfall confirms no fresh liquidity to defend the move. The triple interaction isolates an asymmetric liquidity vacuum: crowded upside gaps devoid of follow-through volume are unwound as cautious macro players sell the rip, yielding a low-risk intraday mean-reversion.

**Implementation (Qlib)**: `If(And(Less(Ts_Percentile($volume,5,50),Ref(Ts_Percentile($volume,5,50),1)),Greater(Delta($open,$close)/Ref($close,1),0.005)),-1*CSRank(Delta($open,$close)/Ref($close,1))*CSRank(Delta($volume,5)-Ts_Percentile(Delta($volume,5),5,80)),0)`

**Math Formula**: Factor_t = -\text{Rank}(\text{OpenGap}_t) \cdot \text{Rank}(\Delta\text{CancelRatio}_{t,5}) \cdot \mathbb{1}_{\left\{\text{T0\_30min\_Volume}_t < \text{Median}_{k=1}^5(\text{T0\_30min\_Volume}_{t-k})\right\}} \cdot \mathbb{1}_{\left\{\text{OpenGap}_t > 0.005\right\}}

**IC / RankIC**: 0.0260 / 0.0080

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows weak positive IC (0.026) but negligible Rank IC (0.008), indicating poor monotonicity. High RRE (0.83) and PFS1 (0.81) suggest good risk-adjusted returns in top decile, but PFS2 near 0.5 shows no edge in lower deciles. Diversity is extremely low (0.005), implying high concentration and turnover. Code mismatch: hypothesis uses cancelled-order ratio and 30-min volume filter, but code uses total volume percentile and delta-volume rank; signal construction does not match intended logic.

**Suggested Improvements**: Replace volume proxies with actual cancelled-order ratio data; compute 30-minute post-open volume versus 5-day median and embed it as a hard filter (0/1) multiplier; Winsorize gap and cancel-ratio ranks at 1-99 % to reduce noise; test asymmetric decile spreads to verify reversal is strongest in highest-gap/highest-cancel bucket; add sector-neutralization and liquidity screen (dollar-volume > 20-day median) to raise diversity above 0.05; verify turnover and implement 1-day delay to check implementability.
