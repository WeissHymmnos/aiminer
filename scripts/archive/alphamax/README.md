# AlphaMax Optimizer Research Iterations (2026-08 Archive)

## Overview

This directory preserves historical standalone research scripts and audit utilities created during the **AlphaMax** optimization sprint (August 2026). The goal of that sprint was to explore portfolio optimization frontiers (targeting annualized return 50%, Sharpe >= 7, MDD < 1%) across discovered alpha factors.

Subsequent rigorous audit (`alphamax_audit.py`, `docs/notes/alphamax-audit-20260822.md`) revealed critical methodology flaws in early iterations (EWMA return smoothing inflating Sharpe by ~3x, in-sample lookahead, missing transaction and leverage costs). Later iterations (`v7`, `v8`) corrected these into an honest, walk-forward out-of-sample framework.

These scripts are kept strictly for historical research reference, reproducibility, and methodology auditing.

## Archived Scripts

| Script | Purpose & Methodology |
|---|---|
| `alphamax_optimize.py` | Initial exploration script for multi-factor portfolio optimization. |
| `alphamax_v2.py` | All-star IC selection with covariance optimization. |
| `alphamax_v3.py` | Iterative factor selection with greedy forward step and correlation filtering. |
| `alphamax_v4.py` | Shrinkage MVO (Ledoit-Wolf) + EWMA return smoothing. |
| `alphamax_v5.py` | Daily volatility targeting (VT) over shrinkage portfolio. |
| `alphamax_v6.py` | High leverage (4.1x) + drawdown brake circuit breaker. |
| `alphamax_audit.py` | Rigorous 5-point financial logic audit uncovering Sharpe inflation and lookahead flaws. |
| `alphamax_v7.py` | Honest walk-forward pipeline: monthly rebalance, 1-day execution lag, 10bp transaction cost, no EWMA smoothing. |
| `alphamax_v8_portfolio.py` | Daily walk-forward portfolio generator and live position exporter (`--live`). |

## Key Findings & References

- **Audit Findings**: Detailed breakdown of lookahead bias, smoothing artifacts, and realistic bounds are documented in `docs/notes/alphamax-audit-20260822.md`.
- **Sprint Conclusions**: Final results and evolution across v1-v6 in `docs/notes/alphamax-final-20260822.md`.
- **Production Replacement**: Production factor portfolio management and execution are integrated into the core `aiminer` package (`aiminer.core.portfolio`, `aiminer.manager`).
