---
title: "Volatility-Adjusted Overnight Gap with Liquidity Exhaustion"
slug: "volatility_adjusted_overnight_gap_with_liquidity_exhaustion_iter2"
type: "factor_card"
status: "failed"
summary: "Stocks that gap up overnight (>1%) while 5-day realized vol is in the top quintile and today’s dollar-volume ranks in the bottom quintile versus its 10-day ave…"
updated: "2026-04-13T20:12:00"
tags: ["监测收益率肥尾风险与动态对冲的风险管理专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0402
rank_ic: 0.0143
iteration: 2
is_effective: false
simulated: false
---

**Hypothesis**: Stocks that gap up overnight (>1%) while 5-day realized vol is in the top quintile and today’s dollar-volume ranks in the bottom quintile versus its 10-day average reverse next-day; factor = -Rank(GapUp) * Rank(Vol5) * (-Rank(Delta(DollarVolume,10))) when GapUp>1% and Vol5>80th percentile, else 0.

**Rationale**: With the Fed signaling higher-for-longer and cross-asset vol creeping up, overnight gaps on quiet volume reflect fragile, options-hedge driven moves rather than fundamental buying. GTJA shows high-vol gaps >1% revert when unaccompanied by liquidity; Gu-Kelly confirms liquidity exhaustion is the strongest non-linear predictor of reversal. Cross-sectional ranking neutralizes the rising market-wide vol regime, isolating microstructure fragility where stale gamma longs are unwound once liquidity disappears.

**Implementation (Qlib)**: `If(And(Greater($open/Ref($close,1)-1,0.01),Greater(Std($close,5),Ts_Percentile(Std($close,5),0,80))),-Rank($open/Ref($close,1)-1)*Rank(Std($close,5))*(-Rank($volume/Mean($volume,10)-1)),0)`

**Math Formula**: f_{i,t}=\begin{cases}-\text{Rank}_t\left(\frac{o_{i,t}}{c_{i,t-1}}-1\right)\cdot\text{Rank}_t(\sigma_{i,t}^{(5)})\cdot\left(-\text{Rank}_t\left(\frac{v_{i,t}}{\bar{v}_{i,t}^{(10)}}-1\right)\right)&\text{if }\frac{o_{i,t}}{c_{i,t-1}}-1>0.01\text{ and }\sigma_{i,t}^{(5)}>\Phi_{t}^{(80)}(\sigma^{(5)})\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0402 / 0.0143

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong directional signal (IC 0.0402) but weak rank ordering (Rank IC 0.0143). Zero RRE and PFS indicate no alpha after costs; zero diversity suggests concentration risk. High Sharpe (4.47) and low drawdown (-14.2%) likely stem from sparse signal (only top-vol gap-up days).

**Suggested Improvements**: 1) Relax vol filter to 60th-70th percentile to increase breadth. 2) Replace binary dollar-volume filter with continuous z-score to preserve cross-sectional spread. 3) Add sector-neutral ranking to reduce concentration. 4) Shrink extreme rank weights via sigmoid transform to mitigate turnover. 5) Overlay liquidity screen (ADV > $5M) to lift RRE/PFS above zero.
