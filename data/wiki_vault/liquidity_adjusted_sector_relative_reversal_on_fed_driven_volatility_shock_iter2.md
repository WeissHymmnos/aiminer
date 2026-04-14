---
title: "Liquidity-Adjusted Sector-Relative Reversal on Fed-Driven Volatility Shock"
slug: "liquidity_adjusted_sector_relative_reversal_on_fed_driven_volatility_shock_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (TsArgMin($close,5)==1)  (Rank($volume / TsMean($volume,20))<0.2)  Sign(Rank($close/Ref($close,1)) - Rank($close/Ref($clo…"
updated: "2026-04-11T20:50:26.942270"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ts_ArgMin($close,5)==1) * (Rank($volume / Ts_Mean($volume,20))<0.2) * Sign(Rank($close/Ref($close,1)) - Rank($close/Ref($close,1),'sector')) ) goes long (short) stocks that hit a 5-day low today on volume <80 % of 20-day average and whose 1-day return is worse (better) than their sector median, expecting a 2-day bounce when the market digests a dovish Fed surprise amid high implied rates volatility.
**Rationale**: Macro News: May CPI downside miss and Fed dots shift lower have compressed 2-yr real yields >20 bp in a week; futures now price 65 bp cuts by Dec-25 vs 40 bp pre-CPI, creating a steep vol surface in SOFR options (1-m ATM vol >110 % of 2024 mean). Market Analysis: High-vol regime favors short-duration reversal trades because dealer gamma hedging flips sign intraday, amplifying micro-mean-reversion. Academic Insight: Cross-sectional rank orthogonalization neutralizes beta while Ts_ArgMin isolates liquidity-driven capitulation; low volume ensures the move is non-fundamental. Sector-relative sign ensures we fade idiosyncratic under-(out)performance rather than market-wide rotation, avoiding crowded factor decay flagged in prior failures (IC<0.02).
**Implementation (Qlib)**: `Rank(If(And(Equal(Ts_ArgMin($close,5),1),Less(Rank(Div($volume,Mean($volume,20))),0.2)),Sign(Sub(Rank(Div($close,Ref($close,1))),CSRank(Div($close,Ref($close,1))))),0))`
**Math Formula**: R = \text{Rank}\left(\mathbf{1}_{\left\{ \text{Ts_ArgMin}(C_t,5)=1 \right\}} \cdot \mathbf{1}_{\left\{ \text{Rank}\left(\frac{V_t}{\bar{V}_{20}}\right)<0.2 \right\}} \cdot \text{Sign}\left( \text{Rank}\left(\frac{C_t}{C_{t-1}}\right) - \text{Rank}_{\text{sector}}\left(\frac{C_t}{C_{t-1}}\right) \right) \right)
**IC / RankIC**: -0.0000 / 0.0000
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows negligible IC and Rank IC (both 0.0), indicating no predictive power; Sharpe 0.30 is modest but not driven by signal strength; max drawdown –40 % is unacceptable; PFS and diversity at 0 imply no sector neutrality or breadth; hypothesis of a 2-day dovish-Fed bounce is not captured by 1-day forward returns tested.
**Suggested Improvements**: 1) Replace 5-day low filter with z-score of 5-day low distance to avoid binary drop-outs. 2) Use volume spike (e.g., 1.5× 20-day avg) instead of <0.2 to capture capitulation. 3) Rank cross-sectionally within sector & market-cap buckets to ensure neutrality. 4) Shift return horizon to 2–5 days to match intended bounce window. 5) Add implied-rate vol filter (e.g., VIX >20 or MOVE >120) to activate signal only in high-vol regimes. 6) Apply winsorization & z-score standardization to reduce extreme weights. 7) Combine with short-term reversal or earnings-announcement dummy to strengthen signal.
