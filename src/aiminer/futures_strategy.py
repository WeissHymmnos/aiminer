"""Launchable entry for the pool-factor futures super strategy.

Usage:
    python -m aiminer.futures_strategy
    aiminer-futures-strategy
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from aiminer.core.futures_super import (
    run_super_strategy,
    select_strategy_factors,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backtest a futures book built from the existing mined factor pool"
    )
    parser.add_argument(
        "--data-path", default=None, help="Override futures data root"
    )
    parser.add_argument(
        "--db-path", default=None, help="Override alpha_miner.db path"
    )
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--max-factors", type=int, default=10)
    parser.add_argument("--screen-candidates", type=int, default=120)
    parser.add_argument("--screen-days", type=int, default=756)
    parser.add_argument("--commission-bps", type=float, default=None)
    parser.add_argument("--slippage-bps", type=float, default=None)
    parser.add_argument("--target-ann-vol", type=float, default=0.0)
    parser.add_argument(
        "--combo-weights",
        default="equal",
        choices=("equal", "delayed_ic"),
    )
    parser.add_argument("--max-per-family", type=int, default=20)
    parser.add_argument("--freq", default="1d", help="1d or 5min")
    parser.add_argument(
        "--universe",
        default="contracts",
        choices=("all_contracts", "contracts", "dominant"),
    )
    parser.add_argument("--min-hold-bars", type=int, default=None)
    parser.add_argument(
        "--neutralize",
        default="none",
        choices=("none", "product"),
        help="none = global CS; product = long-short inside each underlying",
    )
    parser.add_argument(
        "--engine", default="pandas", choices=("pandas", "polars")
    )
    parser.add_argument(
        "--factors-out",
        default=None,
        help="Write resolved factor id/expression list to this path",
    )
    return parser


def format_report(result: dict) -> str:
    metrics = result["metrics"]
    lines = [
        "FUTURES SUPER STRATEGY",
        f"data_source: {result['source'].get('kind')} {result['source'].get('path')}",
        f"universe: {result['source'].get('universe', result.get('freq'))}",
        f"date_range: {result['date_start']} .. {result['date_end']}",
        f"bar_count: {result['bar_count']}",
        f"intraday_bars: {result.get('intraday_bars', result['bar_count'])}",
        f"freq: {result.get('freq', '1d')}",
        f"n_instruments: {result['n_instruments']}",
        f"n_rolls: {result['n_rolls']}",
        f"n_factors: {len(result['factors'])}",
        f"min_hold_bars: {result.get('min_hold_bars', 1)}",
        f"selection: {result.get('selection', 'stored_ic')}",
        f"screen_days: {result.get('screen_days', '')}",
        f"neutralize: {result.get('neutralize', 'none')}",
        "factors_used:",
    ]
    for factor in result["factors"]:
        delayed = factor.get("delayed_ic")
        delayed_txt = f"{delayed:.4f}" if delayed is not None else "na"
        lines.append(
            f"  {factor['id']}\tstored_ic={factor['ic']:.4f}\tdelayed_ic={delayed_txt}\t{factor['expression']}"
        )
    lines.extend(
        [
            f"commission_bps: {result['commission_bps']}",
            f"slippage_bps: {result['slippage_bps']}",
            f"target_ann_vol: {result['target_ann_vol']}",
            f"combo_weights: {result.get('combo_weights', 'equal')}",
            f"Sharpe: {metrics['sharpe']:.6f}",
            f"annualized_return: {metrics['annualized_return']:.6f}",
            f"max_drawdown: {metrics['max_drawdown']:.6f}",
            f"win_rate: {metrics['win_rate']:.6f}",
            f"net_return_sum: {metrics['net_return_sum']:.6f}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_factors_list(result: dict, path: str | Path) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = ["id\tstored_ic\tdelayed_ic\tis_simulated\texpression"]
    for factor in result["factors"]:
        delayed = factor.get("delayed_ic")
        delayed_txt = f"{float(delayed):.6f}" if delayed is not None else "nan"
        lines.append(
            f"{factor['id']}\t{factor['ic']:.6f}\t{delayed_txt}\t0\t{factor['expression']}"
        )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_super_strategy(
        data_path=args.data_path,
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date,
        max_factors=args.max_factors,
        screen_candidates=args.screen_candidates,
        screen_days=args.screen_days,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        target_ann_vol=args.target_ann_vol,
        combo_weights=args.combo_weights,
        max_per_family=args.max_per_family,
        freq=args.freq,
        universe=args.universe,
        neutralize=args.neutralize,
        min_hold_bars=args.min_hold_bars,
        engine=args.engine,
    )
    report = format_report(result)
    sys.stdout.write(report)
    if args.factors_out:
        write_factors_list(result, args.factors_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
