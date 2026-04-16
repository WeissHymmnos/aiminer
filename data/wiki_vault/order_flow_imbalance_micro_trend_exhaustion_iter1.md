---
title: "Order-Flow Imbalance Micro-Trend Exhaustion"
slug: "order_flow_imbalance_micro_trend_exhaustion_iter1"
type: "factor_card"
status: "failed"
summary: "Stocks showing extreme positive order-flow imbalance (Sign(Close-Open)*Volume) over the last 3 days but whose latest 30-minute closing strength (Close-Low)/(Hi…"
updated: "2026-04-13T20:11:39"
tags: ["利用订单流不平衡捕获微观趋势的盘口专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.025
rank_ic: 0.095
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Stocks showing extreme positive order-flow imbalance (Sign(Close-Open)*Volume) over the last 3 days but whose latest 30-minute closing strength (Close-Low)/(High-Low) is below its 5-day average tend to reverse next-day; factor = Rank(Sign(Close-Open)*Volume)/Rank(Ref(Close-Open,1)*Ref(Volume,1)+Ref(Close-Open,2)*Ref(Volume,2)) * -Rank((Close-Low)/(High-Low) - Ts_Mean((Close-Low)/(High-Low),5))

**Rationale**: Central-bank caution caps broad risk appetite, keeping intraday moves short-lived; high-frequency desks fade any micro-trend once cumulative order-flow imbalance peaks yet the auction fails to print at the top of the range, signalling latent supply. By scaling raw imbalance by its 3-day persistence and then contrasting current closing strength against its 5-day norm, the factor isolates micro-exhaustion without double-ranking same-direction variables, avoiding the prior failure while still anchoring on Gu-Kelly liquidity interaction and GTJA closing-strength metrics.

**Implementation (Qlib)**: `Rank(Sign($close - $open) * $volume) / Rank(Sign(Ref($close, 1) - Ref($open, 1)) * Ref($volume, 1) + Sign(Ref($close, 2) - Ref($open, 2)) * Ref($volume, 2)) * (-Rank(($close - $low) / ($high - $low) - Mean(($close - $low) / ($high - $low), 5)))`

**Math Formula**: F_{t}=\frac{\text{rank}\left(\text{sign}(C_{t}-O_{t})\cdot V_{t}\right)}{\text{rank}\left(\text{sign}(C_{t-1}-O_{t-1})\cdot V_{t-1}+\text{sign}(C_{t-2}-O_{t-2})\cdot V_{t-2}\right)}\cdot\left(-\text{rank}\left(\frac{C_{t}^{\text{30m}}-L_{t}^{\text{30m}}}{H_{t}^{\text{30m}}-L_{t}^{\text{30m}}}-\frac{1}{5}\sum_{i=0}^{4}\frac{C_{t-i}^{\text{30m}}-L_{t-i}^{\text{30m}}}{H_{t-i}^{\text{30m}}-L_{t-i}^{\text{30m}}}\right)\right)

**IC / RankIC**: -0.0250 / 0.0950

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong reversal signal with Rank IC 0.095 and LLM score 86.79, but negative IC -0.025 suggests directional inconsistency. High PFS2 0.928 and RRE 0.409 indicate good stability. Diversity 0.259 is acceptable. The negative IC conflicts with hypothesis of positive reversal, suggesting factor construction error in sign handling.

**Suggested Improvements**: Remove negative sign from final rank term to align IC with hypothesis; consider using z-score normalization instead of rank for better symmetry; add sector-neutral ranking to reduce industry bias; test alternative volume weighting schemes like sqrt(volume) to reduce outlier impact; verify 30-minute interval calculation matches intended methodology
