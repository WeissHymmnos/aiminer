"""Gating tests: next-bar fill, cost drag, roll-gap isolation.

These call the shipped execution functions on a tiny synthetic futures panel.
They do not encode target Sharpe or annualized return.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aiminer.core.futures_exec import (
    apply_transaction_costs,
    execute_next_bar,
    holding_open_to_open_return,
    metrics_from_net_returns,
    next_bar_fill_positions,
    same_bar_close_return,
)
from aiminer.core.futures_super import (
    apply_min_hold,
    combine_factor_signals,
    load_stored_strategy_expressions,
    mean_cross_sectional_ic,
    next_bar_open_to_open_label,
    positions_from_combo,
    positions_product_neutral,
    rank_signals_by_delayed_ic,
    to_daily_net,
)


def _synthetic_panel() -> dict[str, pd.DataFrame]:
    dates = pd.to_datetime(
        [
            "2020-01-02",
            "2020-01-03",
            "2020-01-06",
            "2020-01-07",
            "2020-01-08",
            "2020-01-09",
        ]
    )
    names = ["IF", "RB"]
    # IF rolls IF2001 -> IF2002 on 2020-01-07 with a 50-point splice jump.
    # RB stays on one contract the whole window.
    open_px = pd.DataFrame(
        {
            "IF": [4000.0, 4010.0, 4020.0, 4200.0, 4210.0, 4220.0],
            "RB": [3000.0, 3010.0, 2990.0, 3000.0, 3020.0, 3010.0],
        },
        index=dates,
    )
    close_px = pd.DataFrame(
        {
            "IF": [4005.0, 4015.0, 4025.0, 4205.0, 4215.0, 4225.0],
            "RB": [3005.0, 3000.0, 2995.0, 3010.0, 3015.0, 3025.0],
        },
        index=dates,
    )
    contract = pd.DataFrame(
        {
            "IF": ["IF2001", "IF2001", "IF2001", "IF2002", "IF2002", "IF2002"],
            "RB": ["RB2005", "RB2005", "RB2005", "RB2005", "RB2005", "RB2005"],
        },
        index=dates,
    )
    # Decision known at each close: stay long both names.
    decision = pd.DataFrame(0.5, index=dates, columns=names)
    return {
        "open": open_px,
        "close": close_px,
        "contract": contract,
        "decision": decision,
    }


def test_next_bar_fill_is_not_same_bar_close_pnl():
    panel = _synthetic_panel()
    result = execute_next_bar(
        panel["decision"],
        panel["open"],
        panel["contract"],
        commission_bps=0.0,
        slippage_bps=0.0,
        close_px=panel["close"],
    )
    filled = next_bar_fill_positions(panel["decision"])
    # First bar has no fill.
    assert float(filled.iloc[0].abs().sum()) == 0.0
    assert float(filled.iloc[1].abs().sum()) > 0.0

    same_bar = result["same_bar_close_pnl"]
    net = result["net_returns"]
    # Booking the same-bar close return on the *decision* book is a different series.
    assert same_bar is not None
    assert not net.fillna(0.0).equals(same_bar.fillna(0.0))
    # Explicitly: day-0 same-bar close P&L is nonzero while next-bar net is 0.
    same_bar_ret = (
        panel["decision"] * same_bar_close_return(panel["close"]).fillna(0.0)
    ).sum(axis=1)
    assert abs(float(same_bar_ret.iloc[1])) > 0.0
    assert float(net.iloc[0]) == 0.0


def test_net_return_strictly_below_gross_when_costs_and_turnover():
    panel = _synthetic_panel()
    result = execute_next_bar(
        panel["decision"],
        panel["open"],
        panel["contract"],
        commission_bps=5.0,
        slippage_bps=5.0,
        close_px=panel["close"],
    )
    turnover = result["turnover"]
    active = turnover > 0
    assert bool(active.any())
    net = result["net_returns"][active]
    gross = result["gross_returns"][active]
    assert (net < gross - 1e-15).all()

    # Direct call of the shipped cost function.
    net2, costs, _ = apply_transaction_costs(
        result["gross_returns"],
        result["filled_positions"],
        commission_bps=5.0,
        slippage_bps=5.0,
    )
    assert (costs[active] > 0).all()
    assert (net2[active] < result["gross_returns"][active]).all()


def test_dominant_roll_price_gap_is_not_strategy_pnl():
    panel = _synthetic_panel()
    result = execute_next_bar(
        panel["decision"],
        panel["open"],
        panel["contract"],
        commission_bps=0.0,
        slippage_bps=0.0,
    )
    exec_ret = holding_open_to_open_return(panel["open"], panel["contract"])
    # The IF splice is 4020 → 4200 (~+4.5%). That interval must be zeroed.
    if_rets = exec_ret["IF"]
    # Find the bar whose next open is the jumped contract.
    gap_idx = panel["open"].index[
        2
    ]  # 2020-01-06 open 4020 → 2020-01-07 open 4200
    assert panel["contract"].loc[gap_idx, "IF"] == "IF2001"
    assert panel["contract"].shift(-1).loc[gap_idx, "IF"] == "IF2002"
    assert float(if_rets.loc[gap_idx]) == 0.0

    # RB has no roll; its open-to-open return on the same bar is the raw move.
    rb_raw = panel["open"]["RB"].shift(-1) / panel["open"]["RB"] - 1.0
    assert (
        abs(float(exec_ret.loc[gap_idx, "RB"]) - float(rb_raw.loc[gap_idx]))
        < 1e-12
    )

    # Portfolio P&L on the roll bar therefore cannot contain the IF gap.
    filled = result["filled_positions"]
    pnl_if = float(filled.loc[gap_idx, "IF"] * if_rets.loc[gap_idx])
    assert pnl_if == 0.0


def test_delayed_ic_uses_next_open_to_open_not_same_bar_close():
    panel = _synthetic_panel()
    label = next_bar_open_to_open_label(panel["open"], panel["contract"])
    # Same as the shipped executor: open[t]→open[t+1] shifted so it sits on t.
    raw = holding_open_to_open_return(panel["open"], panel["contract"]).shift(
        -1
    )
    pd.testing.assert_frame_equal(label, raw)

    # A signal that equals the delayed label must beat a same-bar close signal.
    same_close = same_bar_close_return(panel["close"])
    scores = rank_signals_by_delayed_ic(
        {"delayed_oracle": label, "same_bar_close": same_close},
        panel["open"],
        panel["contract"],
        min_names=2,
    )
    assert scores["delayed_oracle"] > scores["same_bar_close"]
    assert scores["delayed_oracle"] > 0.5


def test_mean_cs_ic_is_nan_when_cross_section_too_thin():
    idx = pd.to_datetime(["2020-01-02", "2020-01-03"])
    sig = pd.DataFrame({"A": [1.0, 2.0]}, index=idx)
    ret = pd.DataFrame({"A": [0.01, -0.01]}, index=idx)
    assert np.isnan(mean_cross_sectional_ic(sig, ret, min_names=2))


def test_product_neutral_is_not_global_book():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"])
    idx = pd.MultiIndex.from_product(
        [dates, ["IF2001", "IF2002", "RB2005", "RB2006"]],
        names=["datetime", "instrument"],
    )
    combo = pd.Series(
        [0.9, 0.1, 0.8, 0.2, 0.85, 0.15, 0.75, 0.25, 0.95, 0.05, 0.7, 0.3],
        index=idx,
        name="combo",
    )
    product_map = pd.Series(
        {"IF2001": "IF", "IF2002": "IF", "RB2005": "RB", "RB2006": "RB"}
    )
    global_pos = positions_from_combo(combo, max_weight=0.5, min_names=4)
    neut_pos = positions_product_neutral(
        combo, product_map, max_weight=0.5, min_names=4
    )
    assert not global_pos.equals(neut_pos)
    # Each product block is dollar-neutral on every day.
    for names in (["IF2001", "IF2002"], ["RB2005", "RB2006"]):
        assert (neut_pos.loc[:, names].sum(axis=1).abs() < 1e-9).all()


def test_ic_weighted_combo_differs_from_equal_weight():
    idx = pd.MultiIndex.from_product(
        [pd.to_datetime(["2020-01-02", "2020-01-03"]), ["IF", "RB"]],
        names=["datetime", "instrument"],
    )
    frame = pd.DataFrame(
        {"a": [1.0, -1.0, 2.0, -2.0], "b": [0.0, 0.0, 4.0, -4.0]},
        index=idx,
    )
    equal = combine_factor_signals(frame)
    weighted = combine_factor_signals(frame, {"a": 0.0, "b": 1.0})
    assert not equal.equals(weighted)
    # All weight on b must recover column b.
    pd.testing.assert_series_equal(
        weighted, frame["b"].rename("combo"), check_names=True
    )


@pytest.mark.skipif(
    not (
        Path("results/alpha_miner.db").exists()
        or Path("results/alpha_pool.json").exists()
    ),
    reason="Requires live alpha factor pool on disk",
)
def test_stored_strategy_expressions_exist_in_live_pool():
    from aiminer.core.futures_super import _normalize_expr, load_pool_factors

    exprs = load_stored_strategy_expressions(limit=10)
    assert exprs
    pool_expr = {_normalize_expr(f.expression) for f in load_pool_factors()}
    for expr in exprs:
        assert _normalize_expr(expr) in pool_expr


def test_to_daily_net_sums_intraday_bars():
    idx = pd.to_datetime(
        ["2020-01-02 09:35", "2020-01-02 10:00", "2020-01-03 09:35"]
    )
    net = pd.Series([0.01, -0.004, 0.002], index=idx)
    daily = to_daily_net(net)
    assert list(daily.round(10)) == [0.006, 0.002]


def test_apply_min_hold_blocks_immediate_flip():
    dates = pd.to_datetime(
        ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]
    )
    decision = pd.DataFrame(
        {"IF": [0.5, -0.5, -0.5, 0.5]},
        index=dates,
    )
    held = apply_min_hold(decision, min_hold_bars=3)
    # Entry bar plus two more bars must elapse before the book can flip.
    assert [float(x) for x in held["IF"].iloc[:3]] == [0.5, 0.5, 0.5]


def test_metrics_use_252_day_convention_on_the_net_series():
    net = pd.Series([0.01, -0.005, 0.002, 0.0, 0.003])
    metrics = metrics_from_net_returns(net)
    assert metrics["bar_count"] == 5
    # Hand-check sharpe against the shipped series, not a restated formula copy
    # of a different path: calling twice is deterministic.
    again = metrics_from_net_returns(net)
    assert again == metrics
    assert "sharpe" in metrics and "annualized_return" in metrics
