---
title: "Cross-Sector Defensive Quality Flow"
slug: "cross_sector_defensive_quality_flow_iter1"
type: "factor_card"
status: "failed"
summary: "Rank( If( Greater( SectorBetaSPX, 0.9 ), If( Greater( DivYield, SectorMedianDivYield ), Rank( Ts_Mean( Volume, 5 ) / Ts_Mean( Volume, 20 ) ) * Sign( Delta( Clo…"
updated: "2026-04-14T12:08:28"
tags: ["基于宏观周期切换的行业中性专家", "ricequant"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.0
rank_ic: 0.0
iteration: 1
is_effective: false
simulated: false
---

**Hypothesis**: Rank( If( Greater( SectorBetaSPX, 0.9 ), If( Greater( DivYield, SectorMedianDivYield ), Rank( Ts_Mean( Volume, 5 ) / Ts_Mean( Volume, 20 ) ) * Sign( Delta( Close, 10 ) ), NaN ), NaN ) ) goes long high-dividend stocks inside high-beta cyclical sectors only when their 5-day volume is expanding vs 20-day and the stock has fallen in the last 10 days; universe is sector-neutralized and cash-like sectors (utilities, consumer-staples) are excluded.

**Rationale**: With global PMI sliding below 48 and the Fed on hold, investors are rotating from cyclicals into defensives but still need to harvest carry. Within beaten-up cyclical sectors (energy, materials, industrials) the highest-dividend names act as ‘bond proxies’ and attract relative bid when volume re-accelerates after a 10-day pullback, indicating fresh institutional re-allocation rather than passive de-risking. The factor isolates this cross-sector quality flow while maintaining sector neutrality, avoiding overcrowded low-beta staples and capturing bounce-backs supported by real liquidity rather than short-covering noise.

**Implementation (Qlib)**: `Rank(If(And(Greater(0.9,0.9),Greater($close,Median($close))),Rank(Mean($volume,5)/Mean($volume,20))*Sign(Delta($close,10)),0))`

**Math Formula**: R_{t}=\text{rank}_{\text{sector},t}\left[\mathbb{1}_{\{\beta_{i,t}^{\text{SPX}}>0.9\}}\cdot\mathbb{1}_{\{D_{i,t}>\tilde{D}_{\text{sector},t}\}}\cdot\text{rank}_{\text{sector},t}\left(\frac{\frac{1}{5}\sum_{k=1}^{5}V_{i,t-k+1}}{\frac{1}{20}\sum_{k=1}^{20}V_{i,t-k+1}}\right)\cdot\text{sign}\left(C_{i,t}-C_{i,t-10}\right)\right]

**IC / RankIC**: 0.0000 / 0.0000

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor is flat: IC≈0, Rank IC≈0, RRE=0, Sharpe 0.30 but max drawdown -40%. The coded logic is broken (hard-coded 0.9>0.9 is always false, so signal is always 0). No exposure to intended dividend/volume/momentum interaction.

**Suggested Improvements**: Fix the boolean: replace Greater(0.9,0.9) with Greater(SectorBetaSPX,0.9) and Greater($close,Median($close)) with Greater(DivYield,SectorMedianDivYield). Add sector filter to drop utilities & staples. Replace final 0 with NaN to avoid ranking zeros. Consider shorter delta look-back and volume ratio cap to reduce noise.
