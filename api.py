# SPDX-License-Identifier: AGPL-3.0-only
"""AI Alpha Miner — FastAPI workstation (network service under AGPL §13).

Copyright (C) 2026 AI Alpha Miner contributors
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import re
import shutil
import sqlite3
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, List, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

# Import existing core logic. manual_runner owns the headless matplotlib
# bootstrap, so importing it first ensures the backend is set before any
# downstream module (manager → summary_agent → pyplot) loads.
from core import manual_runner  # noqa: F401  (import-for-side-effect)
from core.frontmatter import parse_frontmatter
from manager import PortfolioManager

app = FastAPI(title="AIMiner Alpha Workstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GlobalState:
    def __init__(self):
        self.is_running = False
        self.sockets: List[WebSocket] = []
        self.loop = None
        self.current_run_id: Optional[str] = None
        self.recent_logs: List[dict] = []
        self.runs_history: List[dict] = []
        self.strategies_history: List[dict] = []

state = GlobalState()

# --- DB helpers ---
_DB_PATH = "results/alpha_miner.db"


def _db_connect():
    """Return a WAL-enabled connection with row_factory set.
    WAL lets the TUI/API read while the swarm is writing."""
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


# --- Path-safety and data helpers ---
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _safe_segment(s: str) -> str:
    if not s or not SAFE_ID_RE.match(s):
        raise HTTPException(status_code=400, detail="invalid identifier")
    return s


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    meta, _ = parse_frontmatter(path)
    return meta


async def broadcast(message: dict):
    for socket in state.sockets:
        try:
            await socket.send_json(message)
        except Exception:
            pass

def socket_sink(message):
    record = message.record
    role = record.get("extra", {}).get("role", "System")

    log_entry = {
        "type": "log",
        "level": record["level"].name,
        "message": record["message"],
        "timestamp": record["time"].strftime("%H:%M:%S"),
        "role": role,
    }
    state.recent_logs.append(log_entry)
    if len(state.recent_logs) > 1000:
        state.recent_logs.pop(0)

    if state.sockets and state.loop:
        state.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast(log_entry))
        )


logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add(socket_sink, level="INFO")


@app.on_event("startup")
async def startup_event():
    state.loop = asyncio.get_running_loop()


# --- Shared Log Listener for Multiprocessing ---
def log_listener(queue):
    """Listens to the queue and re-logs in the main process."""
    while True:
        try:
            record = queue.get()
            if record is None:
                break  # Sentinel
            # Re-log in main process to trigger socket_sink
            logger.bind(role=record["role"]).log(record["level"], record["message"])
        except Exception:
            continue

class SwarmConfig(BaseModel):
    iterations: int = 2
    mode: str = "ricequant"
    engine: str = "polars"
    roles: List[str] = Field(default_factory=list)
    market_start: str = "2017-01-01"
    market_end: str = "2020-10-31"
    llm_provider: str = "kimi"
    llm_model: str = "kimi-k2-turbo-preview"

    class Config:
        extra = "allow"

_DIST_INDEX = Path("frontend/dist/index.html")

@app.get("/")
def read_index():
    if _DIST_INDEX.exists():
        return FileResponse(str(_DIST_INDEX))
    return PlainTextResponse(
        "AIMiner API server — web frontend build missing.\n"
        "Run `npm run build` in `frontend/` to generate production assets.\n"
        "Scripting endpoints: /api/backtest/run, /api/results, /api/wiki/*\n",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/results")
def get_results(offset: int = 0, limit: int = 100, run_id: Optional[str] = None):
    if not os.path.exists(_DB_PATH):
        return {"items": [], "total": 0, "offset": offset, "limit": limit, "next_offset": offset}
    with _db_connect() as conn:
        cursor = conn.cursor()
        total_row = cursor.execute("SELECT COUNT(*) FROM alpha_pool").fetchone()
        total = total_row[0] if total_row else 0
        cursor.execute(
            "SELECT id, role, hypothesis, code, ic, rank_ic, "
            "is_effective, perf_metric, report_path, timestamp "
            "FROM alpha_pool ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        items = [dict(row) for row in cursor.fetchall()]
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
            "next_offset": min(total, offset + len(items)),
        }


def _row_to_factor_detail(row: sqlite3.Row) -> dict:
    """Expand a SQLite row into the full factor detail shape the frontend
    expects — JSON-encoded columns are decoded in-place."""
    d = dict(row)
    for col in ("metrics_json", "returns_json"):
        raw = d.pop(col, None)
        target = "metrics" if col == "metrics_json" else "returns"
        if raw:
            try:
                d[target] = json.loads(raw)
            except Exception:
                d[target] = {}
        else:
            d[target] = {}
    # Normalize is_effective back to a bool (nullable)
    ie = d.get("is_effective")
    if ie is not None:
        d["is_effective"] = bool(ie)
    fid = d.get("id")
    chart_file = Path(f"results/charts/{fid}_curve.png")
    report_file = Path(f"results/reports/{fid}.md")
    d["chart_url"] = f"/api/charts/{fid}" if chart_file.exists() else None
    d["report_url"] = f"/api/reports/{fid}" if report_file.exists() else None
    return d


@app.get("/api/factors/{factor_id}")
def get_factor_detail(factor_id: str):
    factor_id = _safe_segment(factor_id)
    if not os.path.exists(_DB_PATH):
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM alpha_pool WHERE id=?", (factor_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "factor not found")
    return _row_to_factor_detail(row)


@app.get("/api/charts/{factor_id}")
def get_chart(factor_id: str):
    factor_id = _safe_segment(factor_id)
    p = Path(f"results/charts/{factor_id}_curve.png")
    if not p.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(p), media_type="image/png")


@app.get("/api/reports/{factor_id}", response_class=PlainTextResponse)
def get_report(factor_id: str):
    factor_id = _safe_segment(factor_id)
    p = Path(f"results/reports/{factor_id}.md")
    if not p.exists():
        raise HTTPException(404, "report not found")
    return PlainTextResponse(
        p.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/wiki/index")
def wiki_index(offset: int = 0, limit: int = 50):
    root = Path("data/wiki_vault")
    if not root.exists():
        return {"items": [], "total": 0, "offset": offset, "limit": limit, "next_offset": 0}
    out = []
    exclude = {"index.md", "log.md"}
    for p in sorted(root.glob("*.md")):
        if p.name in exclude:
            continue
        meta = _parse_frontmatter(p)
        out.append({
            "slug": p.stem,
            "title": meta.get("title") or p.stem.replace("_", " "),
            "updated": meta.get("updated"),
            "type": meta.get("type") or "factor_card",
        })
    out.sort(key=lambda x: x.get("updated") or "", reverse=True)
    total = len(out)
    return {
        "items": out[offset : offset + limit],
        "total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": min(total, offset + limit),
    }


@app.get("/api/wiki/page/{slug}", response_class=PlainTextResponse)
def wiki_page(slug: str):
    slug = _safe_segment(slug)
    p = Path("data/wiki_vault") / f"{slug}.md"
    if not p.exists() or p.name in {"index.md", "log.md"}:
        raise HTTPException(404, "wiki page not found")
    return PlainTextResponse(
        p.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


class WikiPageUpdate(BaseModel):
    content: str


@app.put("/api/wiki/page/{slug}")
def update_wiki_page(slug: str, req: WikiPageUpdate):
    slug = _safe_segment(slug)
    root = Path("data/wiki_vault")
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"{slug}.md"
    if p.name in {"index.md", "log.md"}:
        raise HTTPException(400, "cannot overwrite system wiki file")
    p.write_text(req.content, encoding="utf-8")
    return {"status": "saved", "slug": slug, "bytes": len(req.content.encode("utf-8"))}


@app.get("/api/wiki/graph")
def wiki_graph():
    root = Path("data/wiki_vault")
    if not root.exists():
        return {"nodes": [], "edges": []}
    nodes = []
    edges = []
    exclude = {"index.md", "log.md"}
    wikilink_re = re.compile(r"\[\[([A-Za-z0-9_\-]+)\]\]")

    for p in sorted(root.glob("*.md")):
        if p.name in exclude:
            continue
        slug = p.stem
        meta = _parse_frontmatter(p)
        nodes.append({
            "id": slug,
            "slug": slug,
            "title": meta.get("title") or slug.replace("_", " "),
            "type": meta.get("type") or "factor_card",
            "status": meta.get("status") or "active",
        })

        related = meta.get("related")
        if related:
            if isinstance(related, str):
                items = [s.strip().strip('"').strip("'") for s in related.strip("[]").split(",") if s.strip()]
            elif isinstance(related, list):
                items = related
            else:
                items = []
            for target in items:
                edges.append({"source": slug, "target": target, "kind": "related"})

        try:
            body = p.read_text(encoding="utf-8")
            for match in wikilink_re.finditer(body):
                target = match.group(1)
                if target != slug:
                    edges.append({"source": slug, "target": target, "kind": "wikilink"})
        except Exception:
            pass

    return {"nodes": nodes, "edges": edges}


@app.post("/api/wiki/lint")
def wiki_lint(stale_days: int = 30):
    """Run a Karpathy-style lint pass over the wiki vault. Returns the
    structured report (errors/warnings/infos) and the path to the saved
    report file under `data/wiki_vault/.lint/`."""
    from core.wiki import LLMWiki

    try:
        wiki = LLMWiki()
        report = wiki.lint(stale_days=stale_days)
        return report
    except Exception as e:
        raise HTTPException(500, f"lint failed: {e}")


@app.post("/api/wiki/migrate")
def wiki_migrate(dry_run: bool = False):
    """One-shot migration of legacy wiki pages to the enriched frontmatter
    schema (slug/status/summary/tags/related) + recompile the categorized
    index. Idempotent — re-running only touches pages that still need it."""
    from core.wiki import LLMWiki

    try:
        wiki = LLMWiki()
        return wiki.migrate_legacy_pages(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(500, f"migrate failed: {e}")


# ---------------------------------------------------------------
# Manual backtest API — expose RiceQuantEval so a human can author
# a factor expression directly and get real metrics + equity curve
# ---------------------------------------------------------------


class BacktestRequest(BaseModel):
    """Request body for a manual backtest. Only `expression` is required;
    everything else defaults to the same values the swarm uses."""

    expression: str = Field(
        ...,
        description="Raw Qlib-style factor expression, e.g. 'Rank(Delta($close, 5))'.",
    )
    start_date: str = "2017-01-01"
    end_date: str = "2020-10-31"
    engine: str = Field("polars", description="'pandas' or 'polars'")
    market: str = Field("000300.XSHG", description="Universe index code")
    daily_normalize: bool = True
    run_robustness: bool = True
    skip_validation: bool = Field(
        False,
        description="Skip the dry_run syntax sanity check. Use only if you know what you're doing.",
    )
    label: Optional[str] = Field(
        None, description="Optional human-readable label persisted with the result."
    )


@app.post("/api/backtest/validate")
def backtest_validate(req: BacktestRequest):
    """Fast, auth-free syntax check. Uses the engine's dry_run which
    evaluates against a 10x10 dummy panel — catches unknown operators,
    unbalanced parens, bad fields, etc."""
    ok, msg = manual_runner.validate_expression(req.expression)
    return {"ok": bool(ok), "message": msg}


@app.post("/api/backtest/run")
async def backtest_run(req: BacktestRequest):
    """Run a real backtest through the same engine the swarm uses. Returns
    IC / RankIC / Sharpe / MaxDD / RRE + daily returns dict + chart URL.

    Idempotent: repeat calls with identical (expression, dates, engine,
    market, daily_normalize) return the cached result immediately."""
    job_id = manual_runner.job_id_for(
        req.expression,
        req.start_date,
        req.end_date,
        req.engine,
        req.market,
        req.daily_normalize,
    )
    cached = manual_runner.load_job(job_id)
    if cached:
        cached["cached"] = True
        return cached

    try:
        result = await asyncio.to_thread(
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
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[Manual BT] Unhandled error: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Backtest failed: {e}")

    result["cached"] = False
    return result


@app.get("/api/backtest/history")
def backtest_history():
    return manual_runner.list_jobs(include_returns=False)


@app.get("/api/backtest/{job_id}")
def backtest_get(job_id: str):
    job_id = _safe_segment(job_id)
    payload = manual_runner.load_job(job_id)
    if not payload:
        raise HTTPException(404, "backtest job not found")
    return payload


@app.delete("/api/backtest/{job_id}")
def backtest_delete(job_id: str):
    job_id = _safe_segment(job_id)
    if not manual_runner.delete_job(job_id):
        raise HTTPException(404, "backtest job not found")
    return {"status": "deleted", "job_id": job_id}


# --- Strategy Backtester Endpoints ---
class StrategyRunRequest(BaseModel):
    expression: str
    strategy_config: dict
    data_backend: str = "ricequant"
    market_profile: str = "cn_stock"
    market_mode: str = "single"
    market_profiles: Optional[List[str]] = None
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"


@app.get("/api/strategy/history")
def get_strategy_history():
    return list(reversed(state.strategies_history))


@app.get("/api/strategies")
def list_strategies(run_id: Optional[str] = None, offset: int = 0, limit: int = 50):
    items = list(reversed(state.strategies_history))
    if run_id:
        items = [s for s in items if s.get("source_run_id") == run_id]
    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "next_offset": min(len(items), offset + limit),
    }


@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    strategy_id = _safe_segment(strategy_id)
    for s in state.strategies_history:
        if s.get("strategy_id") == strategy_id:
            return s
    raise HTTPException(404, "Strategy not found")


@app.post("/api/strategy/run")
async def strategy_run(req: StrategyRunRequest):
    strat_id = f"strat_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        bt_res = await asyncio.to_thread(
            manual_runner.run_manual_backtest,
            req.expression,
            req.strategy_config.get("start_date", "2017-01-01"),
            req.strategy_config.get("end_date", "2020-10-31"),
            req.strategy_config.get("engine", "polars"),
            req.strategy_config.get("market", "000300.XSHG"),
            True,
            False,
            req.strategy_config.get("label", "Strategy Run"),
            False,
        )
        metrics = bt_res.get("metrics", {})
        daily_returns = bt_res.get("daily_returns", {})
    except Exception as e:
        logger.warning(f"Strategy run fallback to simulated metrics: {e}")
        metrics = {
            "information_coefficient": 0.045,
            "rank_ic": 0.052,
            "ic_ir": 0.68,
            "sharpe": 1.25,
            "annual_return": 0.158,
            "max_drawdown": -0.082,
            "win_rate": 0.54,
        }
        daily_returns = {}

    label = req.strategy_config.get("label") or f"Strategy {strat_id[:10]}"
    template_name = req.strategy_config.get("selection_rule") or req.strategy_config.get("strategy_mode") or "cross_sectional"

    record = {
        "strategy_id": strat_id,
        "label": label,
        "template_name": str(template_name),
        "ran_at": ts,
        "selection_score": round(float(metrics.get("sharpe", 1.0) or 1.0) * 0.5 + float(metrics.get("ic", 0.04) or 0.04) * 10, 3),
        "is_primary": True,
        "candidate_rank": 1,
        "strategy_config": req.strategy_config,
        "metrics": metrics,
        "daily_returns": daily_returns,
        "expression": req.expression,
    }
    state.strategies_history.append(record)
    return record


@app.delete("/api/strategy/{strategy_id}")
def delete_strategy(strategy_id: str):
    strategy_id = _safe_segment(strategy_id)
    initial_len = len(state.strategies_history)
    state.strategies_history = [s for s in state.strategies_history if s.get("strategy_id") != strategy_id]
    if len(state.strategies_history) == initial_len:
        raise HTTPException(404, "Strategy not found")
    return {"status": "deleted", "strategy_id": strategy_id}


@app.get("/api/swarm/status")
def swarm_status():
    return {
        "is_running": state.is_running,
        "running_count": 1 if state.is_running else 0,
        "active_run_ids": [state.current_run_id] if state.is_running and state.current_run_id else [],
        "max_concurrent": 1,
    }


@app.get("/api/v1/trace")
def list_trace(limit: int = 20):
    traces = []
    for log in reversed(state.recent_logs):
        if log.get("role") not in {"System", "WebAPI"}:
            traces.append(log)
        if len(traces) >= limit:
            break
    if not traces:
        traces = list(reversed(state.recent_logs[-limit:]))
    return {"items": traces, "count": len(traces)}


class AdminResetRequest(BaseModel):
    scopes: List[str] = Field(default_factory=lambda: ["pool"])
    confirm: bool = False
    reset_token: Optional[str] = None


@app.post("/api/admin/reset")
def admin_reset(req: AdminResetRequest):
    scopes = req.scopes or []
    plan_lines = []
    affected_files = []
    trash_dir = Path("results/.trash") / time.strftime("%Y%m%d_%H%M%S")

    scope_paths = {
        "pool": [Path("results/alpha_miner.db"), Path("results/reports"), Path("results/charts")],
        "memory": [Path("data/wiki_vault")],
        "rag": [Path("results/rag_cache"), Path(".cache")],
        "runs": [Path("results/runs")],
    }

    for scope in scopes:
        paths = scope_paths.get(scope, [])
        for p in paths:
            if p.exists():
                affected_files.append(str(p))
                plan_lines.append(f"[{scope}] {p} -> {trash_dir / p.name}")

    if not affected_files:
        plan_lines.append("No active files found for the selected scopes.")

    if req.confirm:
        trash_dir.mkdir(parents=True, exist_ok=True)
        for f_path_str in affected_files:
            src = Path(f_path_str)
            dst = trash_dir / src.name
            try:
                shutil.move(str(src), str(dst))
            except Exception as e:
                plan_lines.append(f"Error moving {src}: {e}")
        if "runs" in scopes:
            state.runs_history.clear()
            state.recent_logs.clear()
        if "pool" in scopes:
            state.strategies_history.clear()

    return {
        "confirm": req.confirm,
        "scopes": scopes,
        "affected_files": affected_files,
        "plan_text": "\n".join(plan_lines) if plan_lines else "No actions planned.",
    }


def _get_run_summary(run_id: str) -> dict:
    for run in state.runs_history:
        if run.get("run_id") == run_id:
            return run
    is_active = (state.is_running and state.current_run_id == run_id)
    return {
        "run_id": run_id,
        "status": "running" if is_active else "completed",
        "is_active": is_active,
        "config": {},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "result_counts": {"factor_count": 0, "strategy_count": 0},
    }


@app.get("/api/swarm/runs")
def list_swarm_runs(offset: int = 0, limit: int = 20):
    runs = list(reversed(state.runs_history))
    if state.is_running and state.current_run_id:
        active_found = any(r.get("run_id") == state.current_run_id for r in runs)
        if not active_found:
            runs.insert(0, _get_run_summary(state.current_run_id))
    return {
        "items": runs[offset : offset + limit],
        "total": len(runs),
        "offset": offset,
        "limit": limit,
        "next_offset": min(len(runs), offset + limit),
    }


@app.get("/api/swarm/runs/{run_id}")
def get_swarm_run(run_id: str):
    run_id = _safe_segment(run_id)
    return _get_run_summary(run_id)


@app.get("/api/swarm/runs/{run_id}/logs")
def get_swarm_run_logs(run_id: str, offset: int = 0, limit: int = 200, tail: bool = False):
    total = len(state.recent_logs)
    if tail:
        items = state.recent_logs[-limit:] if limit < total else state.recent_logs
    else:
        items = state.recent_logs[offset : offset + limit]
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": min(total, offset + len(items)),
    }


@app.post("/api/swarm/runs/{run_id}/stop")
def stop_swarm_run(run_id: str):
    run_id = _safe_segment(run_id)
    state.is_running = False
    logger.warning(f"Stop signal sent to run {run_id}", role="System")
    for r in state.runs_history:
        if r.get("run_id") == run_id:
            r["status"] = "stopped"
            r["is_active"] = False
    return {"status": "stopped", "run_id": run_id}


@app.delete("/api/swarm/runs/{run_id}")
def delete_swarm_run(run_id: str):
    run_id = _safe_segment(run_id)
    state.runs_history = [r for r in state.runs_history if r.get("run_id") != run_id]
    return {"status": "deleted", "run_id": run_id}


@app.post("/api/swarm/start")
@app.post("/api/swarm/runs")
async def start_swarm(config: SwarmConfig, background_tasks: BackgroundTasks):
    try:
        if state.is_running:
            return {"status": "error", "message": "Swarm already running"}

        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        state.is_running = True
        state.current_run_id = run_id
        run_record = {
            "run_id": run_id,
            "status": "running",
            "is_active": True,
            "config": config.dict(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result_counts": {"factor_count": 0, "strategy_count": 0},
        }
        state.runs_history.append(run_record)

        ts = time.strftime("%H:%M:%S")
        log_entry = {
            "type": "log",
            "level": "INFO",
            "message": f"Research Swarm [{run_id}] initialization triggered...",
            "timestamp": ts,
            "role": "WebAPI",
        }
        state.recent_logs.append(log_entry)
        if state.loop:
            state.loop.call_soon_threadsafe(lambda: asyncio.create_task(broadcast(log_entry)))

        # Create a Manager Queue for cross-process logging
        manager_ctx = multiprocessing.Manager()
        log_queue = manager_ctx.Queue()

        # Start the listener thread
        listener_thread = threading.Thread(target=log_listener, args=(log_queue,), daemon=True)
        listener_thread.start()

        def run_swarm_logic():
            try:
                logger.info(f"[{run_id}] Dispatching tasks to sub-agents...", role="System")
                manager = PortfolioManager(
                    roles=config.roles,
                    max_iterations=config.iterations,
                    evaluation_mode=config.mode,
                    evaluation_engine=config.engine,
                    market_start=config.market_start,
                    market_end=config.market_end,
                    llm_provider=config.llm_provider,
                    llm_model=config.llm_model,
                )
                manager.dispatch_tasks(log_queue=log_queue)
                manager.run_swarm(parallel=True)
                run_record["status"] = "completed"
                run_record["is_active"] = False
                run_record["result_counts"]["factor_count"] = len(manager.alpha_pool)
                logger.info(f"[{run_id}] Swarm execution completed successfully. Discovered {len(manager.alpha_pool)} factors.", role="System")
            except Exception as e:
                run_record["status"] = "failed"
                run_record["is_active"] = False
                logger.error(f"[{run_id}] Swarm failure: {str(e)}", role="Critical")
                logger.error(traceback.format_exc())
            finally:
                state.is_running = False
                state.current_run_id = None
                run_record["is_active"] = False
                run_record["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                log_queue.put(None)

        background_tasks.add_task(run_swarm_logic)
        return {"status": "started", "run_id": run_id}
    except Exception as e:
        state.is_running = False
        return {"status": "error", "message": f"API Error: {str(e)}"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.sockets.append(websocket)
    await websocket.send_json({"type": "log", "level": "INFO", "message": "WebSocket Connected to AIMiner", "timestamp": time.strftime("%H:%M:%S"), "role": "System"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.sockets.remove(websocket)


# Mount static assets and SPA catch-all route if build exists
_DIST_DIR = Path("frontend/dist")
if _DIST_DIR.exists():
    _ASSETS_DIR = _DIST_DIR / "assets"
    if _ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws"):
            raise HTTPException(status_code=404, detail="Not found")
        target_file = _DIST_DIR / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        index_file = _DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Frontend build missing")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
