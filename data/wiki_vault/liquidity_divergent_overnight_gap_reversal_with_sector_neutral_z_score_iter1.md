---
title: "Liquidity-Divergent Overnight Gap Reversal with Sector-Neutral Z-Score"
slug: "liquidity_divergent_overnight_gap_reversal_with_sector_neutral_z_score_iter1"
type: "factor_card"
status: "failed"
summary: "Among stocks that open with a positive gap ≥0.5%, those whose overnight gap rank rises while their 1-day turnover rank simultaneously falls (indicating liquidi…"
updated: "2026-04-13T20:11:59"
tags: ["基于宏观周期切换的行业中性专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: -0.029
rank_ic: 0.105
iteration: 1
is_effective: false
simulated: true
---

**Hypothesis**: Among stocks that open with a positive gap ≥0.5%, those whose overnight gap rank rises while their 1-day turnover rank simultaneously falls (indicating liquidity withdrawal) reverse intraday; factor = Zscore_cross(OpenGap) * (-Zscore_cross(Delta(Turnover,1))) when OpenGap>0.5%, else 0, computed within each GICS sector to neutralize industry drift.

**Rationale**: With the central bank on hold and macro uncertainty high, volatility is compressed and capital rotates quickly out of crowded winners. An overnight gap signals consensus momentum, but a simultaneous drop in turnover (liquidity divergence) shows that fewer shares are changing hands to validate the move—hinting at stale aggressive bids. Sector-neutral z-scoring isolates this microstructure exhaustion from broader sector rotation, improving signal robustness versus the prior double-rank approach that muted the contrarian interaction.

**Implementation (Qlib)**: `If(Greater(($open - Ref($close,1)) / Ref($close,1), 0.005), CSZScore(($open - Ref($close,1)) / Ref($close,1)) * (-CSZScore(Delta($volume,1) / Ref($volume,1))), 0)`

**Math Formula**: F_{i,t}=\begin{cases}Z_{\text{OG},s}\left(\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\right)\cdot\left(-Z_{\text{TO},s}\left(\frac{T_{i,t}-T_{i,t-1}}{T_{i,t-1}}\right)\right)&\text{if }\frac{O_{i,t}-C_{i,t-1}}{C_{i,t-1}}\geq 0.005\\0&\text{otherwise}\end{cases}

**IC / RankIC**: -0.0290 / 0.1050

**Effectiveness**: ❌ FAILED

**Review Summary**: Factor shows strong rank IC (0.105) and excellent PFS metrics (>0.63 & >0.96), but negative IC (-0.029) contradicts the long hypothesis; the reversal signal appears to work directionally opposite to intended. RRE (0.42) and diversity (0.354) are acceptable. LLM score (86.33) indicates good code quality.

**Suggested Improvements**: Flip the sign of the factor to align with observed negative IC: use -Zscore_cross(OpenGap) * (-Zscore_cross(Delta(Turnover,1))) or equivalently Zscore_cross(OpenGap) * Zscore_cross(Delta(Turnover,1)). Consider tightening the gap threshold from 0.5% to 0.3-0.4% to increase sample size, and test smoothing turnover delta over 2-3 days to reduce noise. Validate on out-of-sample data to confirm reversal persists after sign correction.
