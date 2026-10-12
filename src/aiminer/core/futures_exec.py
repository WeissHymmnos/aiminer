"""Rigorous futures execution: next-bar fills, costs, roll-aware marks.

Decision-time information is never filled on the same bar. Positions decided
at bar t are filled on bar t+1. Holding P&L is open[t] → open[t+1] only when
the dominant contract is unchanged across that interval; a splice/roll gap
is booked as 0, not as profit. Commission and slippage are charged on
turnover of the filled book.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from aiminer.core.constants import TRADING_DAYS_PER_YEAR


def next_bar_fill_positions(decision_positions: pd.DataFrame) -> pd.DataFrame:
    """Shift decision weights so they first appear on the next tradable bar."""
    return decision_positions.shift(1).fillna(0.0)


def same_bar_close_return(close_px: pd.DataFrame) -> pd.DataFrame:
    """Look-ahead / same-bar close-to-close return (for contrast tests only)."""
    return close_px / close_px.shift(1) - 1.0


def holding_open_to_open_return(
    open_px: pd.DataFrame,
    contract_id: pd.DataFrame,
) -> pd.DataFrame:
    """Return earned from this bar's open to the next bar's open.

    If the dominant contract changes between those two opens, the interval
    crosses a roll/splice and the return is forced to 0 so the price gap is
    not booked as strategy P&L.
    """
    raw = open_px.shift(-1) / open_px - 1.0
    same_contract = contract_id.eq(contract_id.shift(-1))
    valid = open_px.notna() & open_px.shift(-1).notna() & same_contract
    return raw.where(valid, 0.0)


def turnover_from_filled(filled_positions: pd.DataFrame) -> pd.Series:
    """One-way gross turnover of the filled book, including the opening trade."""
    delta = filled_positions.diff().abs().sum(axis=1)
    opening = filled_positions.abs().sum(axis=1)
    return delta.fillna(opening)


def apply_transaction_costs(
    gross_returns: pd.Series,
    filled_positions: pd.DataFrame,
    *,
    commission_bps: float,
    slippage_bps: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Subtract commission+slippage from gross. Net is strictly below gross
    whenever turnover and the combined cost rate are both positive."""
    if commission_bps < 0 or slippage_bps < 0:
        raise ValueError("commission_bps and slippage_bps must be >= 0")
    turnover = turnover_from_filled(filled_positions)
    cost_rate = (float(commission_bps) + float(slippage_bps)) / 10000.0
    costs = turnover * cost_rate
    net = gross_returns - costs
    return net, costs, turnover


def execute_next_bar(
    decision_positions: pd.DataFrame,
    open_px: pd.DataFrame,
    contract_id: pd.DataFrame,
    *,
    commission_bps: float,
    slippage_bps: float,
    close_px: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Run the shipped execution path used for reported P&L.

    ``decision_positions[t]`` may use information through bar t (including
    that bar's close). Fills occur at the next bar. Returns are aligned to
    the fill bar.
    """
    aligned_pos = decision_positions.reindex(
        index=open_px.index, columns=open_px.columns
    ).fillna(0.0)
    open_px = open_px.reindex_like(aligned_pos)
    contract_id = contract_id.reindex_like(aligned_pos)

    filled = next_bar_fill_positions(aligned_pos)
    exec_ret = holding_open_to_open_return(open_px, contract_id)
    gross = (filled * exec_ret).sum(axis=1)
    net, costs, turnover = apply_transaction_costs(
        gross,
        filled,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )

    same_bar = None
    if close_px is not None:
        close_px = close_px.reindex_like(aligned_pos)
        same_bar = (
            aligned_pos * same_bar_close_return(close_px).fillna(0.0)
        ).sum(axis=1)

    return {
        "filled_positions": filled,
        "exec_asset_returns": exec_ret,
        "gross_returns": gross,
        "net_returns": net,
        "costs": costs,
        "turnover": turnover,
        "same_bar_close_pnl": same_bar,
    }


def metrics_from_net_returns(net_returns: pd.Series) -> dict[str, float]:
    """Sharpe and annualized return from a costed net series (252-day convention)."""
    series = pd.Series(net_returns).replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {
            "sharpe": 0.0,
            "annualized_return": 0.0,
            "bar_count": 0,
            "net_return_sum": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
        }
    cumulative = (1.0 + series.fillna(0.0)).cumprod()
    std = float(series.std())
    sharpe = (
        float(series.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))
        if std > 1e-12
        else 0.0
    )
    n = int(len(series))
    annualized = (
        float(
            cumulative.iloc[-1] ** (float(TRADING_DAYS_PER_YEAR) / max(n, 1))
            - 1.0
        )
        if not cumulative.empty and float(cumulative.iloc[-1]) > 0
        else 0.0
    )
    max_dd = (
        float((cumulative / cumulative.cummax() - 1.0).min())
        if not cumulative.empty
        else 0.0
    )
    return {
        "sharpe": sharpe,
        "annualized_return": annualized,
        "bar_count": n,
        "net_return_sum": float(series.sum()),
        "win_rate": float((series > 0).mean()),
        "max_drawdown": max_dd,
    }
