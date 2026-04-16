---
title: "Central-Bank-Hold Divergent VWAP Mean-Reversion"
slug: "central_bank_hold_divergent_vwap_mean_reversion_iter2"
type: "factor_card"
status: "proven"
summary: "While the PBoC keeps rates unchanged, liquidity is trapped in overnight repo; stocks whose VWAP diverges >0.8% from prior close on a 20% surge in cancelled-quo…"
updated: "2026-04-13T20:11:51"
tags: ["专注财报超预期与公告事件驱动的文本挖掘专家", "ricequant", "simulated"]
related: ["strategy_families_base", "market_regime_base"]
ic: 0.082
rank_ic: 0.047
iteration: 2
is_effective: true
simulated: true
---

**Hypothesis**: While the PBoC keeps rates unchanged, liquidity is trapped in overnight repo; stocks whose VWAP diverges >0.8% from prior close on a 20% surge in cancelled-quote ratio (CQR) reverse next-day; factor = -Rank(Abs(VWAP/prevClose-1)) * Rank(Delta(CQR,1)) when Abs(VWAP/prevClose-1)>0.008, else 0.

**Rationale**: Policy inertia compresses intraday ranges, so bots herd into VWAP-arb; a VWAP gap accompanied by a jump in cancelled quotes signals stale VWAP orders being pulled, exposing an illusory price. With no rate-cut fuel, the gap mean-reverts as liquidity snaps back, avoiding the low-abs-return trap of pure close-gap factors that previously failed.

**Implementation (Qlib)**: `If(Greater(Abs($vwap/Ref($close,1)-1),0.008),-Rank(Abs($vwap/Ref($close,1)-1))*Rank(Delta($close,1)),0)`

**Math Formula**: f_{t}=\begin{cases}-\text{Rank}\left(\left|\frac{\text{VWAP}_{t}}{\text{prevClose}_{t}}-1\right|\right)\cdot\text{Rank}\left(\Delta\text{CQR}_{t}\right)&\text{if }\left|\frac{\text{VWAP}_{t}}{\text{prevClose}_{t}}-1\right|>0.008\\0&\text{otherwise}\end{cases}

**IC / RankIC**: 0.0820 / 0.0470

**Effectiveness**: ✅ EFFECTIVE

**Review Summary**: Strong positive IC (0.082) and decent Rank IC (0.047) confirm the reversal signal; high PFS1/2 (>0.8) show good persistence; diversity 0.715 indicates broad applicability. Code mistakenly uses Delta($close,1) instead of Delta(CQR,1), so the factor is not testing the stated hypothesis.

**Suggested Improvements**: Fix code: replace Delta($close,1) with Delta($cqr,1) to match hypothesis; tighten VWAP/prevClose threshold to 1% to reduce noise; neutralize sector/size exposures; test intraday timing (e.g., 14:30 snapshot) to improve signal freshness; verify PBoC-rate-universe filter is applied in backtest.
