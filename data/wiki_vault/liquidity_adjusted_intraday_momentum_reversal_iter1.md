---
title: "Liquidity-Adjusted Intraday Momentum Reversal"
slug: "liquidity_adjusted_intraday_momentum_reversal_iter1"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Stocks whose intraday closing strength (Close-Low)/(High-Low) is high but accompanied by declining liquidity rank over the last…"
updated: "2026-04-13T13:52:06.400729"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Stocks whose intraday closing strength (Close-Low)/(High-Low) is high but accompanied by declining liquidity rank over the last 3 days tend to reverse next-day; factor = Rank(CloseStrength) * (-Rank(Delta(Volume,3))) where negative delta means volume shrinkage.
**Rationale**: Central-bank caution keeps rates steady, curbing broad risk appetite; in this low-vol grind, crowded intraday winners with waning volume are prone to profit-taking. GTJA shows (Close-Low)/(High-Low) captures buying climax, while Gu-Kelly proves liquidity contraction predicts reversals. Cross-sectional ranking neutralizes market drift, letting the factor isolate microstructure exhaustion.
**Implementation (Qlib)**: `Rank(($close - $low) / ($high - $low)) * (-Rank($volume - Ref($volume, 3)))`
**Math Formula**: \text{Factor}_{i,t}=\text{Rank}_{\text{cross}}
\left(\frac{C_{i,t}-L_{i,t}}{H_{i,t}-L_{i,t}}\right)
\times
\left(-\text{Rank}_{\text{cross}}\left(V_{i,t}-V_{i,t-3}\right)\right)
**IC / RankIC**: 0.0024 / 0.0263
**Effectiveness**: ❌ FAILED
**Review Summary**: IC (0.0024) far below 0.02 threshold; negative Sharpe (-0.86) and deep drawdown (-49%) confirm reversal signal is not captured. Factor construction double-ranks same-direction variables, muting the intended contrarian liquidity interaction. Zero PFS/Diversity indicates no portfolio utility.
**Suggested Improvements**: Replace double-rank with z-score standardization; use signed volume change (ΔVol/Vol) instead of raw delta; add sector-neutralization and 20-day liquidity percentile filter; test holding periods 2-5 days; consider intraday version using 5-min close strength to reduce noise.
