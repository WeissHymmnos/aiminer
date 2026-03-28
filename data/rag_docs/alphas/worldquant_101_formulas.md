# WorldQuant Alpha 101 (Qlib Implementation Reference)

This document provides a subset of the famous WorldQuant Alpha 101 formulas translated into Qlib-compatible expressions. These serve as excellent templates for the Idea Agent to construct new factors.

*Note: In Qlib, `Rank` usually computes cross-sectional percentile rank. `Ts_Rank` (or just `Rank` over a window like `Rank($close, d)`) computes time-series rank.*

### Alpha 001
**Idea:** Momentum inversion combined with return rank.
**Qlib Expression:** 
`Rank(Ts_ArgMax(SignedPower(If($close < Ref($close, 1), Std($close, 20), $close), 2), 5)) - 0.5`
*(Simplified for Qlib)*: `Rank(Rank($close) * Rank(Corr($close, $volume, 10)))`

### Alpha 002
**Idea:** Correlation between volume and price change.
**Qlib Expression:**
`-1 * Corr(Rank(Delta(Log($volume), 2)), Rank(($close - $open) / $open), 6)`

### Alpha 003
**Idea:** Mean reversion with volume weighting.
**Qlib Expression:**
`-1 * Corr(Rank($open), Rank($volume), 10)`

### Alpha 004
**Idea:** Low price rank predicting upward movement.
**Qlib Expression:**
`-1 * Ts_Rank(Rank($low), 9)`
*(In Qlib standard operators)*: `-1 * Rank(Rank($low), 9)`

### Alpha 006
**Idea:** Volatility and volume interaction.
**Qlib Expression:**
`-1 * Corr($open, $volume, 10)`

### Alpha 009
**Idea:** High-low spread changes.
**Qlib Expression:**
`If(0 < Min(Delta($close, 1), 5), Delta($close, 1), If(Max(Delta($close, 1), 5) < 0, Delta($close, 1), -1 * Delta($close, 1)))`
*(Approximation using basic operators)*: `Sign(Delta($close, 1)) * Std($close, 5)`

### Alpha 012
**Idea:** Volume momentum.
**Qlib Expression:**
`Sign(Delta($volume, 1)) * (-1 * Delta($close, 1))`

### Alpha 023
**Idea:** Downward momentum based on high prices.
**Qlib Expression:**
`If($high > Mean($high, 20), -1 * Delta($high, 2), 0)`

### Alpha 028
**Idea:** Correlation of volume and trend.
**Qlib Expression:**
`Scale(Corr(Mean($volume, 20), $low, 5) + (Mean($high, 20) + Mean($low, 20)) / 2 - $close)`

### Alpha 041
**Idea:** High price momentum relative to VWAP.
**Qlib Expression:**
`Power($high * $low, 0.5) - $vwap`

### Alpha 054
**Idea:** Price spread relative to close.
**Qlib Expression:**
`-1 * (($low - $close) * Power($open, 5)) / (($low - $high) * Power($close, 5))`

## GTJA 191 Alpha Examples (Chinese Market Focus)

### GTJA Alpha 001
**Idea:** Asymmetric price reversal.
**Qlib Expression:**
`-1 * Corr(Rank(Delta(Log($volume), 1)), Rank(($close - $open) / $open), 6)`

### GTJA Alpha 010
**Idea:** Price acceleration.
**Qlib Expression:**
`Rank(If($close < Ref($close, 1), If($close > Ref($close, 1), Std($close, 20), 0), 0))`
*(Simplified)*: `Std(Max($close - Ref($close, 1), 0), 20)`

### Summary Guidelines for Alpha Mining
1. **Combine Price & Volume:** Factors that combine price momentum with volume changes (using `Corr`, `Cov`, or multiplication) are historically robust.
2. **Neutralization:** Use `Rank()` heavily to neutralize absolute magnitude differences between assets, creating a cross-sectional signal.
3. **Conditionals:** Use `If(condition, true_val, false_val)` to create asymmetric responses to up-days vs down-days.
