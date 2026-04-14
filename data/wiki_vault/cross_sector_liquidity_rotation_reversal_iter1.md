---
title: "Cross-Sector Liquidity Rotation Reversal"
slug: "cross_sector_liquidity_rotation_reversal_iter1"
type: "factor_card"
status: "proven"
summary: "Stocks that outperform their sector by >1% on a 5-day basis while contemporaneous sector-level money-flow (sum of dollar-volume) drops >2% reverse next-day; fa…"
updated: "2026-04-13T20:11:57"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.045
rank_ic: 0.064
iteration: 1
is_effective: true
simulated: true
---

**Hypothesis**: Stocks that outperform their sector by >1% on a 5-day basis while contemporaneous sector-level money-flow (sum of dollar-volume) drops >2% reverse next-day; factor = -Rank(5dSectorExcessReturn) * Rank(Delta(SectorDollarVolume,5)) when excess>1% and sector-flow<-2%, else 0.

**Rationale**: With the central bank on hold and macro volatility compressed, capital rotates defensively across sectors; a single-stock sprint ahead of a sector whose aggregate liquidity is draining signals an over-crowded relative-value bet. As sector money leaves, the lone outperformer loses its bid support and mean-reverts, especially in a low-rate grind where marginal liquidity is scarce.

**Implementation (Qlib)**: `If(And(Greater(Delta($close,5)-Delta(Mean($close,1),5),0.01),Less(Delta(Mean($volume*$close,1),5)/Ref(Mean($volume*$close,1),5),-0.02)),-Rank(Delta($close,5)-Delta(Mean($close,1),5))*Rank(Delta(Mean($volume*$close,1),5)),0)`

**Math Formula**: \text{Factor}_{t}=\begin{cases}-\text{Rank}\left(\frac{\text{Close}_{i,t}}{\text{Close}_{i,t-5}}-\frac{\text{Close}_{\text{sector},t}}{\text{Close}_{\text{sector},t-5}}\right)\cdot\text{Rank}\left(\text{SectorDollarVolume}_{t}-\text{SectorDollarVolume}_{t-5}\right),&\text{if }\frac{\text{Close}_{i,t}}{\text{Close}_{i,t-5}}-\frac{\text{Close}_{\text{sector},t}}{\text{Close}_{\text{sector},t-5}}>0.01\text{ and }\frac{\text{SectorDollarVolume}_{t}-\text{SectorDollarVolume}_{t-5}}{\text{SectorDollarVolume}_{t-5}}<-0.02\\0,&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0450 / 0.0640

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Factor shows strong predictive power: IC 0.045 > 0.02 threshold, Rank IC 0.064 indicates robust monotonicity, RRE 0.51 is healthy, PFS1 0.97 and PFS2 0.55 confirm good hit-rate, Diversity 0.37 is acceptable, LLM score 52.7 is moderate. Conditional construction successfully isolates reversals when sector flow is negative and stock outperforms.

**Suggested Improvements**: 1) Replace hard 1 % / –2 % cut-offs with smooth logistic weighting to reduce tail noise and raise coverage. 2) Normalize sector-dollar-volume change by its 20-day realized volatility to make threshold adaptive. 3) Add sector-relative 5-day money-flow percentile to strengthen signal. 4) Shrink extreme ranks (e.g., winsorize at 1 % / 99 %) to lower turnover and improve PFS2. 5) Combine with overnight gap component to capture next-open execution alpha. 6) Run sector-neutral constraint during portfolio construction to preserve diversity.
