---
title: "Cap-Anchored Liquidity Shock Rebound on Global Trade Weakness"
slug: "cap_anchored_liquidity_shock_rebound_on_global_trade_weakness_iter3"
type: "factor_card"
status: "failed"
summary: "Go long (short) stocks that have underperformed (outperformed) their sector by >3% over the last 10 days while simultaneously experiencing a 20-day low in doll…"
updated: "2026-04-14T12:09:25"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 3
is_effective: false
simulated: false
---

**Hypothesis**: Go long (short) stocks that have underperformed (outperformed) their sector by >3% over the last 10 days while simultaneously experiencing a 20-day low in dollar-volume but only among the top-tercile market-cap names; sign flipped so positive weights to beaten-down large caps with drying liquidity.

**Rationale**: May-13 trade data showed both China exports & US retail sales miss, reinforcing a synchronized global slowdown. Mega-caps with the deepest liquidity pools were used as funding sources during the risk-off, leaving them oversold on thin volume. When macro gloom is fully baked in, the first buyers return to the most liquid, hardest-hit large names; micro/small caps remain orphaned. Sector-neutral cross-sectional rank keeps beta flat, while the 20-day volume low filter isolates liquidity shock rather than chronic decline.

**Implementation (Qlib)**: `If(And(CSRank($close*$volume)>=0.6667,$volume==Ref($volume,19-Ts_ArgMin($volume,19))),Sign(-(Sum($close/Ref($close,10)-1,10)/Sum($close/Ref($close,10)-1,10)-1)-0.03),0)`

**Math Formula**: w_{i,t}=\mathbb{1}_{\text{top-tercile}(\text{Mcap}_{i,t})}\cdot\text{sign}\left(-\left(\frac{r_{i,t-10:t}}{r_{\text{sector}(i),t-10:t}}-1\right)-0.03\right)\cdot\mathbb{1}_{\left\{DVol_{i,t}=\min_{\tau\in[t-19,t]}DVol_{i,\tau}\right\}}

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows zero IC, Rank IC, RRE and Sharpe, indicating no predictive power; the 20-day low dollar-volume filter is too restrictive, collapsing the universe to a handful of stocks and producing flat weights; the sector-relative return z-score construction is circular and always zero, nullifying the intended signal; top-tercile market-cap condition is redundant after liquidity filter; sign flip is applied to a constant zero series.

**Suggested Improvements**: Replace the circular z-score with plain 10-day sector-relative return; relax 20-day low volume to 20-day bottom-quintile or 5-day average < 20-day average; add minimum daily dollar-volume threshold instead of exact low; test 5,10,15-day lookbacks for liquidity trough; verify sector neutrality by ranking within sectors then z-score across; try inverse liquidity percentile rather than binary flag to preserve breadth; add turnover penalty and liquidity smoothing to reduce transaction costs.
