"""Backtest execution, factor pool, and performance analysis APIRouter."""

from __future__ import annotations

import os
from pathlib import Path
import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, PlainTextResponse
from loguru import logger

from aiminer.manager import PortfolioManager
from aiminer.routers.common import *

router = APIRouter(tags=["backtest", "factors"])
backtest_router = router


@backtest_router.get("/api/results")
def get_results(
    run_id: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
) -> Dict[str, Any]:
    if run_id:
        run_id = _safe_segment(run_id)
    if not DB_PATH.exists():
        return _empty_page(offset, limit)
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        existing = _table_columns(conn, "alpha_pool")
        if not existing:
            rows = []
        else:
            select_cols = _select_projection(
                existing, _ALPHA_POOL_RESULT_COLUMNS
            )
            order_clause = (
                "timestamp DESC" if "timestamp" in existing else "rowid DESC"
            )
            if run_id:
                if "run_id" not in existing:
                    rows = []
                else:
                    rows = conn.execute(
                        f"SELECT {select_cols} FROM alpha_pool "
                        f"WHERE run_id=? ORDER BY {order_clause}",
                        (run_id,),
                    ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM alpha_pool "
                    f"ORDER BY {order_clause}"
                ).fetchall()
    return _paginate_rows(list(rows), offset, limit)


@backtest_router.get("/api/factors/{factor_id}")
def get_factor_detail(factor_id: str) -> Dict[str, Any]:
    factor_id = _safe_segment(factor_id)
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        row = conn.execute(
            "SELECT * FROM alpha_pool WHERE id=?", (factor_id,)
        ).fetchone()
        strategy_row = None
        if row and "best_strategy_id" in row.keys() and row["best_strategy_id"]:
            _ensure_strategy_backtests_schema(conn)
            try:
                strategy_row = conn.execute(
                    "SELECT * FROM strategy_backtests WHERE strategy_id=?",
                    (row["best_strategy_id"],),
                ).fetchone()
            except sqlite3.OperationalError:
                strategy_row = None
    if not row:
        raise HTTPException(404, "factor not found")
    payload = _row_to_factor_detail(row)
    if strategy_row:
        payload["best_strategy"] = _row_to_strategy_detail(strategy_row)
    return payload


@backtest_router.post("/api/factors/crossover")
def run_factor_crossover(
    req: FactorCrossoverRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(
        actor,
        "factor.crossover",
        ",".join(req.factor_ids) if req.factor_ids else "alpha_pool_top2",
        {"iterations": req.crossover_iterations},
    )
    parents, factor_pool = _load_crossover_factor_pool(req.factor_ids)
    try:
        manager = PortfolioManager(
            roles=[],
            **_crossover_manager_kwargs(req, parents),
        )
        manager.alpha_pool = list(factor_pool)
        result = manager.run_genetic_crossover(
            parent_factors=parents,
            comparison_pool=factor_pool,
            iterations=req.crossover_iterations,
            persist=True,
            threshold=req.acceptance_threshold,
            agent_id="agent_crossover_pool",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(
            f"[Factor Crossover] Unhandled error: {exc}\n"
            f"{traceback.format_exc()}"
        )
        raise _service_error(exc, "factor crossover failed")

    factor = result.get("factor") or {}
    factor_id = factor.get("id")
    if result.get("status") == "accepted" and factor_id and DB_PATH.exists():
        with _db_connect() as conn:
            _ensure_db_schema(conn)
            row = conn.execute(
                "SELECT * FROM alpha_pool WHERE id=?", (factor_id,)
            ).fetchone()
        if row:
            result["factor"] = _row_to_factor_detail(row)
    return result


@backtest_router.get("/api/charts/{factor_id}")
def get_chart(factor_id: str) -> FileResponse:
    factor_id = _safe_segment(factor_id)
    path = CHART_DIR / f"{factor_id}_curve.png"
    if not path.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(path), media_type="image/png")


@backtest_router.get(
    "/api/reports/{factor_id}", response_class=PlainTextResponse
)
def get_report(factor_id: str) -> PlainTextResponse:
    factor_id = _safe_segment(factor_id)
    path = REPORT_DIR / f"{factor_id}.md"
    if not path.exists():
        raise HTTPException(404, "report not found")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


@backtest_router.post("/api/backtest/validate")
def backtest_validate(
    req: BacktestRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "backtest.validate", "manual", {"label": req.label})
    ok, msg = manual_runner.validate_expression(req.expression)
    return {"ok": bool(ok), "message": msg}


@backtest_router.post("/api/backtest/run")
async def backtest_run(
    req: BacktestRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "backtest.run", "manual", {"label": req.label})
    job_id = manual_runner.job_id_for(
        req.expression,
        req.start_date,
        req.end_date,
        req.engine,
        req.market,
        req.daily_normalize,
        data_backend=req.data_backend,
        market_profile=req.market_profile,
        local_data_path=req.local_data_path,
    )
    cached = manual_runner.load_job(job_id)
    if cached:
        cached["cached"] = True
        return cached
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                manual_runner.run_manual_backtest,
                req.expression,
                req.start_date,
                req.end_date,
                req.engine,
                req.market,
                req.daily_normalize,
                req.run_robustness,
                req.label,
                req.skip_validation,
                req.data_backend,
                req.market_profile,
                req.market_mode,
                req.market_profiles,
                req.local_data_path,
                req.local_data_layout,
            ),
            timeout=MANUAL_BACKTEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"backtest exceeded timeout of "
                f"{MANUAL_BACKTEST_TIMEOUT_SECONDS}s"
            ),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(
            f"[Manual BT] Unhandled error: {exc}\n{traceback.format_exc()}"
        )
        raise _service_error(exc, "backtest failed")
    result["cached"] = False
    return result


@backtest_router.get("/api/backtest/history")
def backtest_history(
    actor: Actor = Depends(_require_actor),
) -> List[Dict[str, Any]]:
    _audit(actor, "backtest.history", "manual")
    return manual_runner.list_jobs(include_returns=False)


@backtest_router.get("/api/backtest/{job_id}")
def backtest_get(
    job_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    job_id = _safe_segment(job_id)
    _audit(actor, "backtest.get", job_id)
    payload = manual_runner.load_job(job_id)
    if not payload:
        raise HTTPException(404, "backtest job not found")
    return payload


@backtest_router.delete("/api/backtest/{job_id}")
def backtest_delete(
    job_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    job_id = _safe_segment(job_id)
    _audit(actor, "backtest.delete", job_id)
    if not manual_runner.delete_job(job_id):
        raise HTTPException(404, "backtest job not found")
    return {"status": "deleted", "job_id": job_id}


# Backward compatibility aliases
run_backtest = backtest_run
validate_backtest = backtest_validate
get_backtest_history = backtest_history
get_backtest_job = backtest_get
delete_backtest_job = backtest_delete
get_factor_chart = get_chart
get_factor_report = get_report
