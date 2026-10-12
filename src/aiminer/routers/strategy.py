"""Strategy optimization, backtest, and portfolio generation APIRouter."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from aiminer.routers.common import *

router = APIRouter(tags=["strategy"])
strategy_router = router


@strategy_router.post("/api/strategy/run")
async def strategy_run(
    req: StrategyRunRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "strategy.run", "manual")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                manual_runner.run_manual_strategy_backtest,
                req.expression,
                req.strategy_config,
                req.data_backend,
                req.market_profile,
                req.market_mode,
                req.market_profiles,
                req.local_data_path,
                req.local_data_layout,
            ),
            timeout=STRATEGY_BACKTEST_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"strategy backtest exceeded timeout of "
                f"{STRATEGY_BACKTEST_TIMEOUT_SECONDS}s"
            ),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(
            f"[Strategy BT] Unhandled error: {exc}\n{traceback.format_exc()}"
        )
        raise _service_error(exc, "strategy backtest failed")
    return result


@strategy_router.get("/api/strategy/history")
def strategy_history(
    actor: Actor = Depends(_require_actor),
) -> List[Dict[str, Any]]:
    _audit(actor, "strategy.history", "manual")
    return manual_runner.list_strategy_jobs(include_returns=False)


@strategy_router.get("/api/strategies")
def get_strategies(
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
        existing = _table_columns(conn, "strategy_backtests")
        if not existing:
            rows = []
        else:
            select_cols = _select_projection(existing, _STRATEGY_LIST_COLUMNS)
            order_clause = (
                "ran_at DESC" if "ran_at" in existing else "rowid DESC"
            )
            if run_id:
                if "run_id" not in existing:
                    rows = []
                else:
                    rows = conn.execute(
                        f"SELECT {select_cols} FROM strategy_backtests "
                        f"WHERE run_id=? ORDER BY {order_clause}",
                        (run_id,),
                    ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM strategy_backtests "
                    f"ORDER BY {order_clause}"
                ).fetchall()
    paged = _paginate_rows(list(rows), offset, limit)
    items: List[Dict[str, Any]] = []
    for row in paged["items"]:
        item = dict(row)
        try:
            item["metrics"] = json.loads(item.pop("metrics_json") or "{}")
        except Exception:
            item["metrics"] = {}
        items.append(item)
    paged["items"] = items
    return paged


@strategy_router.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> Dict[str, Any]:
    strategy_id = _safe_segment(strategy_id)
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        try:
            row = conn.execute(
                "SELECT * FROM strategy_backtests WHERE strategy_id=?",
                (strategy_id,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            logger.warning(f"[schema] failed to read strategy_backtests: {exc}")
            row = None
    if not row:
        raise HTTPException(404, "strategy not found")
    return _row_to_strategy_detail(row)


@strategy_router.delete("/api/strategy/{strategy_id}")
def delete_strategy(
    strategy_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    strategy_id = _safe_segment(strategy_id)
    _audit(actor, "strategy.delete", strategy_id)
    file_deleted = manual_runner.delete_strategy_job(strategy_id)
    deleted_rows = 0
    if DB_PATH.exists():
        with _db_connect() as conn:
            _ensure_strategy_backtests_schema(conn)
            cursor = conn.execute(
                "DELETE FROM strategy_backtests WHERE strategy_id=?",
                (strategy_id,),
            )
            deleted_rows = cursor.rowcount
            conn.commit()
    if not file_deleted and deleted_rows == 0:
        raise HTTPException(404, "strategy backtest not found")
    return {"status": "deleted", "strategy_id": strategy_id}


@strategy_router.get("/api/strategies/{strategy_id}/charts/{kind}")
def get_strategy_chart(strategy_id: str, kind: str) -> FileResponse:
    strategy_id = _safe_segment(strategy_id)
    if kind not in {"equity", "turnover"}:
        raise HTTPException(400, "invalid chart kind")
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_strategy_backtests_schema(conn)
        row = conn.execute(
            "SELECT chart_paths_json FROM strategy_backtests "
            "WHERE strategy_id=?",
            (strategy_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "strategy not found")
    chart_paths = json.loads(row["chart_paths_json"] or "{}")
    path = chart_paths.get(kind)
    if not path or not Path(path).exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(path), media_type="image/png")


# Backward compatibility aliases
run_strategy = strategy_run
run_strategy_backtest = strategy_run
get_strategy_history = strategy_history
get_strategy_detail = get_strategy
list_strategies = get_strategies
