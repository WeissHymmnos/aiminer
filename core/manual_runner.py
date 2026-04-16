"""Shared runner for manual factor and strategy backtests.

Exposes a minimal façade around ``RiceQuantEval`` and the strategy
executor so the TUI and local scripts can trigger, persist, and re-read
the same backtest jobs without duplicating glue code.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Headless matplotlib backend — required whenever this module is imported
# by a server process (uvicorn, Textual worker thread) that has no GUI.
import matplotlib

matplotlib.use("Agg")

MANUAL_DIR = Path("results/manual")
STRATEGY_DIR = Path("results/strategies")
CHART_DIR = Path("results/charts")


# ---------------------------------------------------------------
# Identity + persistence
# ---------------------------------------------------------------


def job_id_for(
    expression: str,
    start_date: str,
    end_date: str,
    engine: str,
    market: str,
    daily_normalize: bool,
    data_backend: str = "ricequant",
    market_profile: str = "cn_stock",
    local_data_path: str | None = None,
) -> str:
    """Deterministic job id — identical params collapse onto the same
    cached result. Prefixed ``manual_`` so it never collides with the
    swarm's ``alpha_*`` ids."""
    key = (
        f"{expression}|{start_date}|{end_date}|{engine}|{market}|{daily_normalize}|"
        f"{data_backend}|{market_profile}|{local_data_path or ''}"
    )
    return "manual_" + hashlib.md5(key.encode()).hexdigest()[:10]


def persist_job(job_id: str, payload: Dict[str, Any]) -> None:
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANUAL_DIR / f"{job_id}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    p = MANUAL_DIR / f"{job_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_jobs(include_returns: bool = False) -> List[Dict[str, Any]]:
    """Return all persisted manual backtests, newest first. Drops the
    heavy ``daily_returns`` dict unless explicitly requested."""
    if not MANUAL_DIR.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in MANUAL_DIR.glob("manual_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not include_returns:
            data = {k: v for k, v in data.items() if k != "daily_returns"}
            data["return_points"] = len(
                (json.loads(p.read_text(encoding="utf-8"))).get("daily_returns") or {}
            )
        out.append(data)
    out.sort(key=lambda x: x.get("ran_at", ""), reverse=True)
    return out


def persist_strategy_job(strategy_id: str, payload: Dict[str, Any]) -> None:
    STRATEGY_DIR.mkdir(parents=True, exist_ok=True)
    with open(STRATEGY_DIR / f"{strategy_id}.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_strategy_job(strategy_id: str) -> Optional[Dict[str, Any]]:
    p = STRATEGY_DIR / f"{strategy_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_strategy_jobs(include_returns: bool = False) -> List[Dict[str, Any]]:
    if not STRATEGY_DIR.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in STRATEGY_DIR.glob("strategy_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not include_returns:
            data = {k: v for k, v in data.items() if k != "daily_returns"}
            data["return_points"] = len(
                (json.loads(p.read_text(encoding="utf-8"))).get("daily_returns") or {}
            )
        out.append(data)
    out.sort(key=lambda x: x.get("ran_at", ""), reverse=True)
    return out


def delete_job(job_id: str) -> bool:
    p = MANUAL_DIR / f"{job_id}.json"
    existed = p.exists()
    if existed:
        p.unlink()
    chart = CHART_DIR / f"{job_id}_curve.png"
    if chart.exists():
        chart.unlink()
    return existed


def delete_strategy_job(strategy_id: str) -> bool:
    p = STRATEGY_DIR / f"{strategy_id}.json"
    existed = p.exists()
    if existed:
        p.unlink()
    for suffix in ("_curve.png", "_turnover.png"):
        chart = CHART_DIR / f"{strategy_id}{suffix}"
        if chart.exists():
            chart.unlink()
    return existed


# ---------------------------------------------------------------
# Syntax validation (fast, no auth)
# ---------------------------------------------------------------


def validate_expression(expression: str) -> Tuple[bool, str]:
    """Run the engine's ``dry_run`` against a 10x10 dummy panel. Catches
    bad fields, unbalanced parens, and most operator typos without
    touching the network."""
    from core.alphaeval.rq_eval import RiceQuantEval

    return RiceQuantEval.dry_run(expression)


# ---------------------------------------------------------------
# Chart generation (PNG — for web/TUI fallback; TUI also renders
# interactively via plotext)
# ---------------------------------------------------------------


def save_equity_curve(returns_series, job_id: str) -> Optional[str]:
    if returns_series is None:
        return None
    if hasattr(returns_series, "empty") and returns_series.empty:
        return None
    import matplotlib.pyplot as plt

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / f"{job_id}_curve.png"
    fig = plt.figure(figsize=(10, 6))
    cum = (1 + returns_series.fillna(0)).cumprod()
    cum.plot(title=f"Equity Curve — {job_id}", grid=True)
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.tight_layout()
    plt.savefig(str(path))
    plt.close(fig)
    return str(path.resolve())


def save_turnover_curve(turnover_series, job_id: str) -> Optional[str]:
    if turnover_series is None:
        return None
    if hasattr(turnover_series, "empty") and turnover_series.empty:
        return None
    import matplotlib.pyplot as plt

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    path = CHART_DIR / f"{job_id}_turnover.png"
    fig = plt.figure(figsize=(10, 4))
    turnover_series.fillna(0.0).plot(title=f"Turnover — {job_id}", grid=True)
    plt.xlabel("Date")
    plt.ylabel("Turnover")
    plt.tight_layout()
    plt.savefig(str(path))
    plt.close(fig)
    return str(path.resolve())


# ---------------------------------------------------------------
# The main entry point
# ---------------------------------------------------------------


def run_manual_backtest(
    expression: str,
    start_date: str = "2017-01-01",
    end_date: str = "2020-10-31",
    engine: str = "pandas",
    market: str = "000300.XSHG",
    daily_normalize: bool = True,
    run_robustness: bool = True,
    label: Optional[str] = None,
    skip_validation: bool = False,
    data_backend: str = "ricequant",
    market_profile: str = "cn_stock",
    market_mode: str = "single",
    market_profiles: Optional[List[str]] = None,
    local_data_path: Optional[str] = None,
    local_data_layout: str = "auto",
    progress_cb=None,
) -> Dict[str, Any]:
    """Synchronously run a single-factor backtest through the real engine.

    ``progress_cb`` (optional) is called with short status strings —
    useful for streaming updates to a live TUI display. Signature:
    ``progress_cb(stage: str, message: str) -> None``.
    """
    from core.evaluator_factory import build_evaluator, evaluation_config_from_mapping

    def emit(stage: str, message: str) -> None:
        if progress_cb is not None:
            try:
                progress_cb(stage, message)
            except Exception:
                pass

    job_id = job_id_for(
        expression,
        start_date,
        end_date,
        engine,
        market,
        daily_normalize,
        data_backend=data_backend,
        market_profile=market_profile,
        local_data_path=local_data_path,
    )
    t0 = time.time()

    if not skip_validation:
        emit("validate", "Running dry-run syntax check…")
        ok, msg = validate_expression(expression)
        if not ok:
            raise ValueError(f"Invalid expression: {msg}")

    emit("init", f"Instantiating evaluator (backend={data_backend}, engine={engine})…")
    evaluator = build_evaluator(
        factor_expressions=[expression],
        config=evaluation_config_from_mapping(
            {
                "data_backend": data_backend,
                "evaluation_engine": engine,
                "market_mode": market_mode,
                "market_profile": market_profile,
                "market_profiles": market_profiles or [market_profile],
                "local_data_path": local_data_path,
                "local_data_layout": local_data_layout,
                "market_start": start_date,
                "market_end": end_date,
            }
        ),
        test_start_date=start_date,
        test_end_date=end_date,
        daily_normalize=daily_normalize,
    )

    emit("fetch", f"Fetching {market} data {start_date} → {end_date}…")
    evaluator.run()

    rre: Optional[float] = None
    if run_robustness:
        emit("robustness", "Running robustness test (noise-injected re-run)…")
        try:
            evaluator.run_robustness_test()
            rre = float(getattr(evaluator, "rre", 0.0))
        except Exception:
            rre = None

    emit("chart", "Rendering equity curve PNG…")
    returns_series = getattr(evaluator, "daily_returns_series", None)
    chart_path = save_equity_curve(returns_series, job_id)

    elapsed = round(time.time() - t0, 2)
    payload: Dict[str, Any] = {
        "job_id": job_id,
        "run_type": "factor_backtest",
        "status": "ok",
        "expression": expression,
        "engine": engine,
        "market": market,
        "period": {"start": start_date, "end": end_date},
        "daily_normalize": daily_normalize,
        "label": label,
        "data_backend": data_backend,
        "market_profile": market_profile,
        "market_mode": market_mode,
        "metrics": {
            "ic": float(getattr(evaluator, "ic", 0.0)),
            "rank_ic": float(getattr(evaluator, "rankic", 0.0)),
            "sharpe": float(getattr(evaluator, "sharpe", 0.0)),
            "max_drawdown": float(getattr(evaluator, "max_dd", 0.0)),
            "rre": rre,
        },
        "daily_returns": getattr(evaluator, "daily_returns", {}) or {},
        "chart_path": chart_path,
        "chart_paths": {"equity": chart_path} if chart_path else {},
        "elapsed_seconds": elapsed,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    persist_job(job_id, payload)
    emit("done", f"Completed in {elapsed}s")
    return payload


def run_manual_strategy_backtest(
    expression: str,
    strategy_config: Dict[str, Any],
    data_backend: str = "ricequant",
    market_profile: str = "cn_stock",
    market_mode: str = "single",
    market_profiles: Optional[List[str]] = None,
    local_data_path: Optional[str] = None,
    local_data_layout: str = "auto",
    progress_cb=None,
) -> Dict[str, Any]:
    from core.evaluator_factory import build_evaluator, evaluation_config_from_mapping
    from core.strategy import (
        StrategyBacktester,
        StrategyConfig,
        persist_strategy_result,
    )

    def emit(stage: str, message: str) -> None:
        if progress_cb is not None:
            try:
                progress_cb(stage, message)
            except Exception:
                pass

    cfg = (
        strategy_config
        if isinstance(strategy_config, StrategyConfig)
        else StrategyConfig.model_validate(strategy_config)
    )
    strategy_key = json.dumps(
        {
            "expression": expression,
            "config": cfg.model_dump(mode="json"),
            "data_backend": data_backend,
            "market_profile": market_profile,
            "market_mode": market_mode,
            "local_data_path": local_data_path,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    strategy_id = "strategy_" + hashlib.md5(strategy_key.encode()).hexdigest()[:10]
    cached = load_strategy_job(strategy_id)
    if cached:
        return cached

    emit("validate", "Running expression dry-run syntax check…")
    ok, msg = validate_expression(expression)
    if not ok:
        raise ValueError(f"Invalid expression: {msg}")

    emit("init", f"Instantiating evaluator (backend={data_backend}, engine={cfg.engine})…")
    evaluator = build_evaluator(
        factor_expressions=[expression],
        config=evaluation_config_from_mapping(
            {
                "data_backend": data_backend,
                "evaluation_engine": cfg.engine,
                "market_mode": market_mode,
                "market_profile": market_profile,
                "market_profiles": market_profiles or [market_profile],
                "local_data_path": local_data_path,
                "local_data_layout": local_data_layout,
                "market_start": cfg.start_date,
                "market_end": cfg.end_date,
            }
        ),
        test_start_date=cfg.start_date,
        test_end_date=cfg.end_date,
        daily_normalize=True,
    )
    emit("fetch", f"Fetching {cfg.market} data {cfg.start_date} → {cfg.end_date}…")
    evaluator.fetch_data()
    evaluator.compute_factors()

    signal_df = evaluator.factor_data.iloc[:, 0].unstack().sort_index()
    label_df = evaluator.label_data["label"].unstack().sort_index()
    emit("strategy", "Constructing portfolio and applying trading costs…")
    result = StrategyBacktester(cfg).run(signal_df, label_df)
    returns_series = result.pop("raw_returns")
    positions_frame = result.pop("raw_positions")

    emit("chart", "Rendering strategy charts…")
    equity_path = save_equity_curve(returns_series, strategy_id)
    turnover_path = save_turnover_curve(
        positions_frame.diff().abs().sum(axis=1).fillna(0.0), strategy_id
    )

    payload: Dict[str, Any] = {
        "strategy_id": strategy_id,
        "run_type": "strategy_backtest",
        "status": "ok",
        "expression": expression,
        "strategy_config": cfg.model_dump(mode="json"),
        "metrics": result["metrics"],
        "daily_returns": result["daily_returns"],
        "positions": result["positions"],
        "trade_stats": result["trade_stats"],
        "chart_paths": {
            "equity": equity_path,
            "turnover": turnover_path,
        },
        "market": cfg.market,
        "engine": cfg.engine,
        "label": cfg.label,
        "data_backend": data_backend,
        "market_profile": market_profile,
        "market_mode": market_mode,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    persist_strategy_job(strategy_id, payload)
    persist_strategy_result(Path("results") / "alpha_miner.db", payload)
    emit("done", "Strategy backtest completed")
    return payload
