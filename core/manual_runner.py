"""Shared runner for manual factor backtests.

Exposes a minimal façade around ``RiceQuantEval`` so both the HTTP API
(``api.py``) and the TUI (``tui.py``) can trigger, persist, and re-read
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
) -> str:
    """Deterministic job id — identical params collapse onto the same
    cached result. Prefixed ``manual_`` so it never collides with the
    swarm's ``alpha_*`` ids."""
    key = f"{expression}|{start_date}|{end_date}|{engine}|{market}|{daily_normalize}"
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


def delete_job(job_id: str) -> bool:
    p = MANUAL_DIR / f"{job_id}.json"
    existed = p.exists()
    if existed:
        p.unlink()
    chart = CHART_DIR / f"{job_id}_curve.png"
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
    progress_cb=None,
) -> Dict[str, Any]:
    """Synchronously run a single-factor backtest through the real engine.

    ``progress_cb`` (optional) is called with short status strings —
    useful for streaming updates to a live TUI display. Signature:
    ``progress_cb(stage: str, message: str) -> None``.
    """
    from core.alphaeval.rq_eval import RiceQuantEval

    def emit(stage: str, message: str) -> None:
        if progress_cb is not None:
            try:
                progress_cb(stage, message)
            except Exception:
                pass

    job_id = job_id_for(
        expression, start_date, end_date, engine, market, daily_normalize
    )
    t0 = time.time()

    if not skip_validation:
        emit("validate", "Running dry-run syntax check…")
        ok, msg = RiceQuantEval.dry_run(expression)
        if not ok:
            raise ValueError(f"Invalid expression: {msg}")

    emit("init", f"Instantiating RiceQuantEval (engine={engine})…")
    evaluator = RiceQuantEval(
        factor_expressions=[expression],
        test_start_date=start_date,
        test_end_date=end_date,
        market=market,
        daily_normalize=daily_normalize,
        engine=engine,
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
        "status": "ok",
        "expression": expression,
        "engine": engine,
        "market": market,
        "period": {"start": start_date, "end": end_date},
        "daily_normalize": daily_normalize,
        "label": label,
        "metrics": {
            "ic": float(getattr(evaluator, "ic", 0.0)),
            "rank_ic": float(getattr(evaluator, "rankic", 0.0)),
            "sharpe": float(getattr(evaluator, "sharpe", 0.0)),
            "max_drawdown": float(getattr(evaluator, "max_dd", 0.0)),
            "rre": rre,
        },
        "daily_returns": getattr(evaluator, "daily_returns", {}) or {},
        "chart_path": chart_path,
        "chart_url": f"/api/charts/{job_id}" if chart_path else None,
        "elapsed_seconds": elapsed,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    persist_job(job_id, payload)
    emit("done", f"Completed in {elapsed}s")
    return payload
