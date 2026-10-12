"""Combine already-mined pool factors into a futures book and backtest it."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

import numpy as np
import pandas as pd

from aiminer.core.futures_exec import (
    execute_next_bar,
    holding_open_to_open_return,
    metrics_from_net_returns,
)
from aiminer.core.futures_panel import (
    load_all_zip_contracts_panel,
    load_contract_panel,
    load_futures_panel,
    load_intraday_panel,
    panel_to_wide,
)

DEFAULT_DB = Path(__file__).resolve().parents[3] / "results" / "alpha_miner.db"
DEFAULT_JSON = (
    Path(__file__).resolve().parents[3] / "results" / "alpha_pool.json"
)

# Expressions known to be slow (rolling apply) — skip so the launch stays cheap.
_SLOW_TOKENS = ("Ts_Rank", "WMA", "Ts_Percentile", "Ts_ArgMax", "Ts_ArgMin")


@dataclass(frozen=True)
class PoolFactor:
    factor_id: str
    expression: str
    ic: float
    is_simulated: int
    market_profile: str
    delayed_ic: float | None = None


def _normalize_expr(expression: str) -> str:
    return "".join(str(expression).split())


def _family(expression: str) -> str:
    text = expression.lower()
    tags: list[str] = []
    if "corr" in text:
        tags.append("corr")
    if "vwap" in text:
        tags.append("vwap")
    if "volume" in text:
        tags.append("vol")
    if "delta" in text or "ref($close" in text.replace(" ", ""):
        tags.append("mom")
    if "high" in text and "low" in text:
        tags.append("range")
    return "+".join(tags) or "other"


def load_pool_factors(
    db_path: str | Path | None = None,
    json_path: str | Path | None = None,
) -> list[PoolFactor]:
    """Load non-simulated futures factors from the existing pool."""
    db = Path(db_path) if db_path else DEFAULT_DB
    rows: list[PoolFactor] = []
    if db.exists():
        with sqlite3.connect(db) as conn:
            cur = conn.execute(
                """
                SELECT id, code, ic, is_simulated, market_profile
                FROM alpha_pool
                WHERE COALESCE(is_simulated, 0) = 0
                  AND market_profile = 'futures'
                  AND code IS NOT NULL
                  AND TRIM(code) != ''
                """
            )
            for fid, code, ic, sim, profile in cur.fetchall():
                rows.append(
                    PoolFactor(
                        factor_id=str(fid),
                        expression=str(code),
                        ic=float(ic or 0.0),
                        is_simulated=int(sim or 0),
                        market_profile=str(profile or ""),
                    )
                )
    if rows:
        return rows

    jpath = Path(json_path) if json_path else DEFAULT_JSON
    if not jpath.exists():
        raise FileNotFoundError(f"Factor pool not found at {db} or {jpath}")
    payload = json.loads(jpath.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("factors", [])
    for item in items:
        if int(item.get("is_simulated") or 0) != 0:
            continue
        if str(item.get("market_profile") or "") != "futures":
            continue
        code = item.get("code") or item.get("expression")
        if not code:
            continue
        rows.append(
            PoolFactor(
                factor_id=str(item.get("id") or item.get("factor_id")),
                expression=str(code),
                ic=float(item.get("ic") or 0.0),
                is_simulated=0,
                market_profile="futures",
            )
        )
    if not rows:
        raise ValueError("No non-simulated futures factors in the pool")
    return rows


def select_strategy_factors(
    pool: Iterable[PoolFactor] | None = None,
    *,
    max_factors: int = 16,
    max_per_family: int = 3,
    db_path: str | Path | None = None,
) -> list[PoolFactor]:
    """Pick diverse high-IC expressions that already live in the pool."""
    factors = (
        list(pool) if pool is not None else load_pool_factors(db_path=db_path)
    )
    live = [f for f in factors if f.is_simulated == 0 and f.expression.strip()]
    live.sort(key=lambda f: f.ic, reverse=True)
    seen_expr: set[str] = set()
    family_count: dict[str, int] = {}
    picked: list[PoolFactor] = []
    for factor in live:
        if any(tok in factor.expression for tok in _SLOW_TOKENS):
            continue
        key = _normalize_expr(factor.expression)
        if key in seen_expr:
            continue
        fam = _family(factor.expression)
        if family_count.get(fam, 0) >= max_per_family:
            continue
        seen_expr.add(key)
        family_count[fam] = family_count.get(fam, 0) + 1
        picked.append(factor)
        if len(picked) >= max_factors:
            break
    if not picked:
        raise ValueError("Factor selection produced an empty set")
    return picked


def next_bar_open_to_open_label(
    open_px: pd.DataFrame,
    contract_id: pd.DataFrame,
) -> pd.DataFrame:
    """Forward return earned by a position filled on the next bar's open.

    ``holding_open_to_open_return[t]`` is open[t]→open[t+1] (roll-zeroed).
    Shifting it by -1 aligns signal[t] with the hold that starts at the
    next tradable open — the same lag the shipped executor uses.
    """
    return holding_open_to_open_return(open_px, contract_id).shift(-1)


def mean_cross_sectional_ic(
    signal: pd.DataFrame,
    forward_return: pd.DataFrame,
    *,
    min_names: int = 8,
) -> float:
    """Average daily Spearman-style Pearson IC of ranks vs next-bar returns."""
    aligned = signal.reindex_like(forward_return)
    ics: list[float] = []
    for ts in aligned.index:
        a = aligned.loc[ts]
        b = forward_return.loc[ts]
        mask = a.notna() & b.notna()
        if int(mask.sum()) < min_names:
            continue
        left = a[mask]
        right = b[mask]
        if int(left.nunique()) < 2 or int(right.nunique()) < 2:
            continue
        corr = float(left.corr(right))
        if np.isfinite(corr):
            ics.append(corr)
    if not ics:
        return float("nan")
    return float(np.mean(ics))


def rank_signals_by_delayed_ic(
    signals: dict[str, pd.DataFrame],
    open_px: pd.DataFrame,
    contract_id: pd.DataFrame,
    *,
    screen_index: pd.Index | None = None,
    min_names: int = 8,
) -> dict[str, float]:
    """Score each signal on next-open-to-open delayed IC (shipped label)."""
    fwd = next_bar_open_to_open_label(open_px, contract_id)
    if screen_index is not None:
        fwd = fwd.loc[fwd.index.intersection(screen_index)]
    scores: dict[str, float] = {}
    for name, frame in signals.items():
        scores[name] = mean_cross_sectional_ic(frame, fwd, min_names=min_names)
    return scores


def _screen_dates(index: pd.Index, screen_days: int) -> pd.Index:
    dates = pd.DatetimeIndex(pd.to_datetime(index)).sort_values().unique()
    if len(dates) == 0:
        return index
    take = max(60, min(int(screen_days), max(len(dates) // 3, 60)))
    return dates[:take]


def select_by_delayed_ic(
    candidates: Iterable[PoolFactor],
    panel: pd.DataFrame,
    *,
    max_factors: int = 6,
    screen_days: int = 756,
    min_names: int = 8,
    max_per_family: int = 3,
    engine: str = "pandas",
) -> list[PoolFactor]:
    """Rebuild the combo from the best next-bar delayed-IC expressions.

    Delayed IC is measured only on the first ``screen_days`` dates so
    selection does not see the later evaluation window. At most
    ``max_per_family`` expressions from the same operator family are kept.
    """
    cand = [f for f in candidates if f.expression.strip()]
    if not cand:
        raise ValueError("No candidates to screen")
    ohlcv = panel[
        [
            "datetime",
            "instrument",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "total_turnover",
        ]
    ].copy()
    factor_df = compute_factor_panel(
        ohlcv, [f.expression for f in cand], engine=engine
    )
    wide = panel_to_wide(panel)
    open_px = wide["open"]
    contract_id = wide["dominant_contract"].reindex_like(open_px)
    screen_index = _screen_dates(open_px.index, screen_days)
    signals = {
        expr: factor_df[expr].unstack("instrument").reindex_like(open_px)
        for expr in factor_df.columns
    }
    scores = rank_signals_by_delayed_ic(
        signals,
        open_px,
        contract_id,
        screen_index=screen_index,
        min_names=min_names,
    )
    by_expr = {_normalize_expr(f.expression): f for f in cand}
    ranked: list[PoolFactor] = []
    family_count: dict[str, int] = {}
    for expr, score in sorted(
        scores.items(),
        key=lambda kv: kv[1] if np.isfinite(kv[1]) else -np.inf,
        reverse=True,
    ):
        if not np.isfinite(score) or score <= 0:
            continue
        base = by_expr.get(_normalize_expr(expr))
        if base is None:
            continue
        fam = _family(base.expression)
        if family_count.get(fam, 0) >= max_per_family:
            continue
        family_count[fam] = family_count.get(fam, 0) + 1
        ranked.append(
            PoolFactor(
                factor_id=base.factor_id,
                expression=base.expression,
                ic=base.ic,
                is_simulated=base.is_simulated,
                market_profile=base.market_profile,
                delayed_ic=float(score),
            )
        )
        if len(ranked) >= max_factors:
            break
    if not ranked:
        raise ValueError("No candidate had positive next-bar delayed IC")
    return ranked


def load_stored_strategy_expressions(
    db_path: str | Path | None = None,
    *,
    limit: int = 20,
) -> list[str]:
    """Expressions of the best stored futures strategy_backtests rows."""
    db = Path(db_path) if db_path else DEFAULT_DB
    if not db.exists():
        return []
    out: list[str] = []
    seen: set[str] = set()
    pool_expr = {_normalize_expr(f.expression) for f in load_pool_factors(db)}
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            """
            SELECT expression_json
            FROM strategy_backtests
            WHERE market_profile = 'futures'
            ORDER BY CAST(
                COALESCE(json_extract(metrics_json, '$.sharpe'), 0) AS REAL
            ) DESC
            """
        ).fetchall()
    for (raw,) in rows:
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            expr = str(raw).strip()
        else:
            if isinstance(payload, dict):
                expr = str(payload.get("expression") or "").strip()
            else:
                expr = str(payload).strip()
        key = _normalize_expr(expr)
        if not expr or key in seen or key not in pool_expr:
            continue
        seen.add(key)
        out.append(expr)
        if len(out) >= limit:
            break
    return out


def assert_factors_in_pool(
    selected: Iterable[PoolFactor],
    *,
    db_path: str | Path | None = None,
) -> list[PoolFactor]:
    """Every selected id/expression must exist in the non-simulated pool."""
    pool = load_pool_factors(db_path=db_path)
    by_id = {f.factor_id: f for f in pool}
    missing: list[str] = []
    for factor in selected:
        row = by_id.get(factor.factor_id)
        if row is None:
            missing.append(factor.factor_id)
            continue
        if row.is_simulated != 0:
            missing.append(f"{factor.factor_id}:simulated")
            continue
        if _normalize_expr(row.expression) != _normalize_expr(
            factor.expression
        ):
            missing.append(f"{factor.factor_id}:expression-mismatch")
    if missing:
        raise AssertionError(f"Strategy factors not in live pool: {missing}")
    return list(selected)


def compute_factor_panel(
    ohlcv: pd.DataFrame,
    expressions: list[str],
    *,
    engine: str = "pandas",
) -> pd.DataFrame:
    """Evaluate pool expressions on the futures book via the shipped engine."""
    from aiminer.core.alphaeval.rq_eval import RiceQuantEval

    raw = ohlcv.copy()
    if not isinstance(raw.index, pd.MultiIndex):
        raw = raw.set_index(["datetime", "instrument"]).sort_index()
    keep = [
        c
        for c in ("open", "high", "low", "close", "volume", "total_turnover")
        if c in raw.columns
    ]
    raw = raw[keep]
    evaluator = RiceQuantEval(
        factor_expressions=expressions,
        skip_auth=True,
        engine=engine,
        daily_normalize=True,
        output_dir=str(
            Path(__file__).resolve().parents[3] / "results" / "reports"
        ),
    )
    evaluator.raw_data = raw
    computed: list[pd.Series] = []
    names: list[str] = []
    # Evaluate one-by-one so a single bad expression does not kill the book.
    for expr in expressions:
        try:
            ev = RiceQuantEval(
                factor_expressions=[expr],
                skip_auth=True,
                engine=engine,
                daily_normalize=True,
                output_dir=evaluator.output_dir,
            )
            ev.raw_data = raw
            ev.compute_factors()
            computed.append(ev.factor_data.iloc[:, 0].rename(expr))
            names.append(expr)
        except Exception:
            continue
    if not computed:
        raise RuntimeError("All selected factor expressions failed to compute")
    return pd.concat(computed, axis=1)


def combine_factor_signals(
    factor_df: pd.DataFrame,
    weights: dict[str, float] | pd.Series | None = None,
) -> pd.Series:
    """Combine daily-zscored factor columns.

    ``weights`` are applied after clipping negatives to 0 and L1-normalizing.
    ``None`` is equal weight (the historical default).
    """
    cleaned = factor_df.replace([np.inf, -np.inf], np.nan)
    if weights is None:
        return cleaned.mean(axis=1, skipna=True).rename("combo")
    series = (
        pd.Series(weights).reindex(cleaned.columns).fillna(0.0).clip(lower=0.0)
    )
    total = float(series.sum())
    if total <= 1e-12:
        return cleaned.mean(axis=1, skipna=True).rename("combo")
    series = series / total
    return cleaned.mul(series, axis=1).sum(axis=1, min_count=1).rename("combo")


def positions_from_combo(
    combo: pd.Series,
    *,
    max_weight: float = 0.08,
    min_names: int = 8,
) -> pd.DataFrame:
    """Cross-sectional rank long-short, dollar-neutral, per-name cap."""
    wide = combo.unstack("instrument")
    ranks = wide.rank(axis=1, pct=True)
    centered = ranks.sub(ranks.mean(axis=1), axis=0)
    valid = wide.notna().sum(axis=1)
    centered = centered.where(valid >= min_names, 0.0)
    # L1-normalize so gross exposure is 1 when the cap allows it.
    gross = centered.abs().sum(axis=1).replace(0.0, np.nan)
    weights = centered.div(gross, axis=0).fillna(0.0)
    weights = weights.clip(lower=-max_weight, upper=max_weight)
    # Re-normalize after the cap so leftover risk is redistributed, then re-cap.
    gross2 = weights.abs().sum(axis=1).replace(0.0, np.nan)
    weights = (
        weights.div(gross2, axis=0)
        .fillna(0.0)
        .clip(lower=-max_weight, upper=max_weight)
    )
    return weights.fillna(0.0)


def positions_product_neutral(
    combo: pd.Series,
    product_map: pd.Series,
    *,
    max_weight: float = 0.05,
    min_names: int = 20,
) -> pd.DataFrame:
    """Rank long-short inside each underlying so we do not take product beta."""
    wide = combo.unstack("instrument")
    prod = product_map.reindex(wide.columns)
    weights = pd.DataFrame(0.0, index=wide.index, columns=wide.columns)
    for _product, cols in prod.groupby(prod):
        names = list(cols.index)
        block = wide[names]
        ranks = block.rank(axis=1, pct=True)
        centered = ranks.sub(ranks.mean(axis=1), axis=0)
        # need at least 2 live contracts to form a spread
        live = block.notna().sum(axis=1)
        centered = centered.where(live >= 2, 0.0)
        gross = centered.abs().sum(axis=1).replace(0.0, np.nan)
        weights[names] = centered.div(gross, axis=0)
    valid = wide.notna().sum(axis=1)
    weights = weights.where(valid >= min_names, 0.0)
    gross = weights.abs().sum(axis=1).replace(0.0, np.nan)
    weights = weights.div(gross, axis=0).fillna(0.0)
    return weights.clip(lower=-max_weight, upper=max_weight).fillna(0.0)


def apply_min_hold(decision: pd.DataFrame, min_hold_bars: int) -> pd.DataFrame:
    """Keep the previous book until ``min_hold_bars`` have elapsed since the last change."""
    if min_hold_bars <= 1:
        return decision.fillna(0.0)
    held = pd.DataFrame(0.0, index=decision.index, columns=decision.columns)
    prev = pd.Series(0.0, index=decision.columns, dtype=float)
    age = 0
    for ts in decision.index:
        cand = decision.loc[ts].fillna(0.0)
        if (
            age < min_hold_bars
            and float((cand - prev).abs().sum()) > 1e-12
            and age > 0
        ):
            held.loc[ts] = prev
            age += 1
            continue
        if float((cand - prev).abs().sum()) > 1e-12:
            age = 1
            prev = cand
        elif float(prev.abs().sum()) > 0:
            age += 1
        held.loc[ts] = prev
    return held.fillna(0.0)


def to_daily_net(net: pd.Series) -> pd.Series:
    """Sum intra-day net returns so Sharpe uses the 252-day convention."""
    series = pd.Series(net).copy()
    series.index = pd.to_datetime(series.index)
    daily = series.groupby(series.index.normalize()).sum().sort_index()
    daily.index.name = "datetime"
    return daily


def causal_vol_leverage(
    unlevered_net: pd.Series,
    *,
    target_ann_vol: float,
    lookback: int = 60,
    max_leverage: float = 12.0,
) -> pd.Series:
    """Scale tomorrow's book with yesterday's realized vol (no look-ahead)."""
    from aiminer.core.constants import TRADING_DAYS_PER_YEAR

    realized = unlevered_net.rolling(
        lookback, min_periods=max(20, lookback // 3)
    ).std()
    ann = realized * np.sqrt(TRADING_DAYS_PER_YEAR)
    leverage = (target_ann_vol / ann.replace(0.0, np.nan)).clip(
        0.0, max_leverage
    )
    # shift(1): today's leverage uses only past returns.
    return leverage.shift(1).fillna(0.0)


def run_super_strategy(
    *,
    data_path: str | None = None,
    db_path: str | Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    max_factors: int = 10,
    screen_candidates: int = 120,
    screen_days: int = 756,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
    target_ann_vol: float = 0.0,
    max_weight: float = 0.35,
    min_hold_bars: int | None = None,
    min_names: int | None = None,
    freq: str = "1d",
    universe: str = "contracts",
    neutralize: str = "none",
    combo_weights: str = "equal",
    max_per_family: int = 20,
    include_stored_strategies: bool = True,
    engine: str = "pandas",
) -> dict[str, Any]:
    """Load pool factors, build the futures book, execute, score.

    Combo membership is the best next-open-to-open delayed-IC expressions
    from a prefix of the panel, not the stored same-close miner IC.
    """
    intraday = freq.lower() not in {"1d", "d", "day", "daily"}
    if commission_bps is None:
        commission_bps = 0.5 if intraday else 1.0
    if slippage_bps is None:
        slippage_bps = 0.5 if intraday else 1.0
    if min_hold_bars is None:
        min_hold_bars = 6 if intraday else 1
    if min_names is None:
        min_names = 3 if intraday else 20

    if intraday:
        panel, source_meta = load_intraday_panel(
            data_path, rule=freq, start_date=start_date, end_date=end_date
        )
    elif universe == "all_contracts":
        zip_arg = None
        if data_path:
            p = Path(data_path).expanduser()
            if p.is_file():
                zip_arg = p
            elif p.is_dir():
                matches = sorted(p.glob("daily_*.zip"))
                zip_arg = matches[0] if matches else p
        panel, source_meta = load_all_zip_contracts_panel(
            zip_arg, start_date=start_date, end_date=end_date
        )
    elif universe == "contracts":
        panel, source_meta = load_contract_panel(
            data_path, start_date=start_date, end_date=end_date
        )
    else:
        panel, source_meta = load_futures_panel(
            data_path, start_date=start_date, end_date=end_date
        )
    source_meta["freq"] = freq
    source_meta["universe"] = universe

    candidates = select_strategy_factors(
        max_factors=screen_candidates,
        max_per_family=max(8, screen_candidates),
        db_path=db_path,
    )
    if include_stored_strategies:
        pool = load_pool_factors(db_path=db_path)
        by_expr = {_normalize_expr(f.expression): f for f in pool}
        have = {_normalize_expr(f.expression) for f in candidates}
        for expr in load_stored_strategy_expressions(db_path, limit=20):
            key = _normalize_expr(expr)
            if key in have:
                continue
            match = by_expr.get(key)
            if match is None:
                continue
            candidates.append(match)
            have.add(key)
    selected = select_by_delayed_ic(
        candidates,
        panel,
        max_factors=max_factors,
        screen_days=screen_days,
        min_names=3 if intraday else 8,
        max_per_family=max_per_family,
        engine=engine,
    )
    assert_factors_in_pool(selected, db_path=db_path)
    source_meta["selection"] = "delayed_open_to_open_ic"
    source_meta["screen_days"] = str(screen_days)
    source_meta["screen_candidates"] = str(len(candidates))
    source_meta["combo_weights"] = combo_weights
    source_meta["max_per_family"] = str(max_per_family)

    ohlcv = panel[
        [
            "datetime",
            "instrument",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "total_turnover",
        ]
    ].copy()
    factor_df = compute_factor_panel(
        ohlcv, [f.expression for f in selected], engine=engine
    )
    if combo_weights == "delayed_ic":
        weight_map = {
            f.expression: float(f.delayed_ic or 0.0) for f in selected
        }
        combo = combine_factor_signals(factor_df, weight_map)
    else:
        combo = combine_factor_signals(factor_df)
    if neutralize == "product" and "product" in panel.columns:
        product_map = (
            panel.sort_values("datetime")
            .groupby("instrument")["product"]
            .last()
        )
        decision = positions_product_neutral(
            combo, product_map, max_weight=max_weight, min_names=min_names
        )
    else:
        decision = positions_from_combo(
            combo, max_weight=max_weight, min_names=min_names
        )
    decision = apply_min_hold(decision, min_hold_bars)
    wide = panel_to_wide(panel)
    open_px = wide["open"].reindex(
        index=decision.index, columns=decision.columns
    )
    contract_id = wide["dominant_contract"].reindex_like(open_px)
    close_px = wide["close"].reindex_like(open_px)

    executed = execute_next_bar(
        decision,
        open_px,
        contract_id,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        close_px=close_px,
    )
    unlevered = executed["net_returns"]
    daily_unlevered = to_daily_net(unlevered)
    if target_ann_vol and target_ann_vol > 0:
        leverage_daily = causal_vol_leverage(
            daily_unlevered, target_ann_vol=target_ann_vol, lookback=60
        )
        bar_dates = pd.to_datetime(unlevered.index).normalize()
        leverage = pd.Series(
            leverage_daily.reindex(bar_dates).to_numpy(), index=unlevered.index
        ).fillna(0.0)
    else:
        leverage_daily = pd.Series(1.0, index=daily_unlevered.index)
        leverage = pd.Series(1.0, index=unlevered.index)

    levered_net = unlevered * leverage
    levered_gross = executed["gross_returns"] * leverage
    levered_costs = executed["costs"] * leverage

    daily_net = to_daily_net(levered_net)
    daily_gross = to_daily_net(levered_gross)
    daily_costs = to_daily_net(levered_costs)
    warmup = int(min(len(daily_net), 40))
    scored = daily_net.iloc[warmup:]
    metrics = metrics_from_net_returns(scored)

    start = scored.index.min() if len(scored) else None
    end = scored.index.max() if len(scored) else None
    return {
        "factors": [
            {
                "id": f.factor_id,
                "expression": f.expression,
                "ic": f.ic,
                "delayed_ic": f.delayed_ic,
            }
            for f in selected
        ],
        "selection": "delayed_open_to_open_ic",
        "screen_days": screen_days,
        "neutralize": neutralize,
        "combo_weights": combo_weights,
        "source": source_meta,
        "metrics": metrics,
        "date_start": str(pd.Timestamp(start).date())
        if start is not None
        else "",
        "date_end": str(pd.Timestamp(end).date()) if end is not None else "",
        "bar_count": int(metrics["bar_count"]),
        "intraday_bars": int(len(unlevered)),
        "n_instruments": int(panel["instrument"].nunique()),
        "n_rolls": int(panel["is_roll"].sum())
        if "is_roll" in panel.columns
        else 0,
        "commission_bps": commission_bps,
        "slippage_bps": slippage_bps,
        "target_ann_vol": target_ann_vol,
        "freq": freq,
        "min_hold_bars": min_hold_bars,
        "net_returns": scored,
        "unlevered_net": daily_unlevered,
        "leverage": leverage_daily,
        "gross_returns": daily_gross.reindex(scored.index),
        "costs": daily_costs.reindex(scored.index),
        "decision_positions": decision,
        "executed": executed,
    }
