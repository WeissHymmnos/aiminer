---
title: "Liquidity-Adjusted Overnight Reversal with Sector Dispersion"
slug: "liquidity_adjusted_overnight_reversal_with_sector_dispersion_iter2"
type: "factor_card"
status: "failed"
summary: "Hypothesis: Rank( (Ref($close,1) - Ref($open,1)) / Ref($close,2)  Sign(0.2 - Rank($volume / Ref($volume,1)))  Sign(Rank($close / Ref($close…"
updated: "2026-04-11T20:50:22.763378"
tags: []
related: ["strategy_families_base"]
---

**Hypothesis**: Rank( (Ref($close,1) - Ref($open,1)) / Ref($close,2) * Sign(0.2 - Rank($volume / Ref($volume,1))) * Sign(Rank($close / Ref($close,1), 'sector') - Rank($close / Ref($close,1))) ) goes long (short) stocks whose overnight gap is large versus prior close, only when concurrent volume spike ranks in bottom 20 % of universe and the stock’s 1-day return ranks above its sector median, expecting that low-volume overnight gaps in leading names quickly revert as liquidity returns and sector dispersion compresses.
**Rationale**: In the current high-volatility bearish regime, overnight gaps driven by low liquidity are more likely to mean-revert as liquidity returns during the day. By focusing on stocks that are outperforming their sector peers, we capture the unwind of temporary overreactions in relatively strong names. The 20 % volume threshold (vs 30 % in failed attempt) better isolates true liquidity droughts, while the sector-relative return ranking ensures we bet on reversals in stocks that have temporarily overshot their fundamental peer group, a pattern common when macro uncertainty compresses sector dispersion.
**Implementation (Qlib)**: `Rank(Multiply(Multiply(Divide(Minus(Ref($close,1),Ref($open,1)),Ref($close,2)),Sign(Minus(0.2,Rank(Divide($volume,Ref($volume,1)))))),Sign(Minus(CSRank(Divide($close,Ref($close,1))),Rank(Divide($close,Ref($close,1)))))))`
**Math Formula**: \text{Signal}_{t} = \text{Rank}\left( \frac{\text{Ref}(C_{t},1) - \text{Ref}(O_{t},1)}{\text{Ref}(C_{t},2)} \cdot \text{Sign}\left(0.2 - \text{Rank}\left(\frac{V_{t}}{\text{Ref}(V_{t},1)}\right)\right) \cdot \text{Sign}\left(\text{Rank}\left(\frac{C_{t}}{\text{Ref}(C_{t},1)},\text{sector}\right) - \text{Rank}\left(\frac{C_{t}}{\text{Ref}(C_{t},1)}\right)\right) \right)
**IC / RankIC**: 0.0007 / 0.0003
**Effectiveness**: ❌ FAILED
**Review Summary**: Factor shows negligible predictive power (IC 0.0007, Rank IC 0.0003) and zero hit-rate metrics (PFS1/2=0), while Sharpe 0.27 is modest and drawdown -42 % is high; diversity 0 % indicates extreme concentration. The overnight-gap signal is drowned by noisy rank interactions and the volume/sector filters appear to remove most actionable names.
**Suggested Improvements**: 1) Replace double-rank sector comparison with raw z-score sector residual to preserve dispersion magnitude. 2) Use a smooth volume-percentile threshold (e.g., <30 % 20-day median) instead of hard 20 % rank to raise breadth. 3) Scale gap by 20-day realized volatility to create a standardized reversal signal. 4) Add liquidity filter (ADV > $5 M) and cap weight at 2 % to cut 42 % drawdown. 5) Combine with short-term mean-reversion alpha (e.g., 5-day RSI <30) to lift IC above 0.02 and raise PFS above 0.5.
