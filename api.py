import os
import json
import re
import sqlite3
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from loguru import logger
import sys
import time
import traceback
import threading
import multiprocessing

# Import existing core logic. manual_runner owns the headless matplotlib
# bootstrap, so importing it first ensures the backend is set before any
# downstream module (manager → summary_agent → pyplot) loads.
from core import manual_runner  # noqa: F401  (import-for-side-effect)
from manager import PortfolioManager
from core.hybrid_knowledge import HybridKnowledge

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


def _parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.lstrip().startswith("---"):
        return {}
    body = text.lstrip()[3:]
    end = body.find("\n---")
    if end < 0:
        return {}
    meta = {}
    for line in body[:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


async def broadcast(message: dict):
    for socket in state.sockets:
        try:
            await socket.send_json(message)
        except:
            pass

def socket_sink(message):
    record = message.record
    # In some contexts extra might be empty
    role = record.get("extra", {}).get("role", "System")
    
    log_entry = {
        "type": "log",
        "level": record["level"].name,
        "message": record["message"],
        "timestamp": record["time"].strftime("%H:%M:%S"),
        "role": role
    }
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
            if record is None: break # Sentinel
            # Re-log in main process to trigger socket_sink
            logger.bind(role=record['role']).log(record['level'], record['message'])
        except Exception:
            continue

class SwarmConfig(BaseModel):
    iterations: int = 2
    mode: str = "ricequant"
    engine: str = "polars"
    roles: List[str]
    market_start: str = "2017-01-01"
    market_end: str = "2020-10-31"
    llm_provider: str = "kimi"
    llm_model: str = "kimi-k2-turbo-preview"

@app.get("/")
def read_index():
    """Root — the web frontend has been replaced by a Textual TUI.
    Run ``python tui.py`` to open it. The ``/api/*`` endpoints below are
    still exposed for scripting / automation."""
    return PlainTextResponse(
        "AIMiner API server — web frontend has moved to `python tui.py`.\n"
        "Scripting endpoints: /api/backtest/run, /api/results, /api/wiki/*\n",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/results")
def get_results():
    if not os.path.exists(_DB_PATH):
        return []
    with _db_connect() as conn:
        cursor = conn.cursor()
        # Exclude bulky returns_json — detail endpoint fetches it on demand.
        cursor.execute(
            "SELECT id, role, hypothesis, code, ic, rank_ic, "
            "is_effective, perf_metric, report_path, timestamp "
            "FROM alpha_pool ORDER BY timestamp DESC"
        )
        return [dict(row) for row in cursor.fetchall()]


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
def wiki_index():
    root = Path("data/wiki_vault")
    if not root.exists():
        return []
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
    return out


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

from core import manual_runner


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


@app.get("/api/swarm/status")
def swarm_status():
    return {"is_running": state.is_running}


@app.post("/api/swarm/start")
async def start_swarm(config: SwarmConfig, background_tasks: BackgroundTasks):
    try:
        if state.is_running:
            return {"status": "error", "message": "Swarm already running"}
        
        state.is_running = True
        ts = time.strftime("%H:%M:%S")
        log_entry = {"type": "log", "level": "INFO", "message": "Research Swarm initialization triggered...", "timestamp": ts, "role": "WebAPI"}
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
                logger.info("Dispatching tasks to sub-agents...", role="System")
                manager = PortfolioManager(
                    roles=config.roles,
                    max_iterations=config.iterations,
                    evaluation_mode=config.mode,
                    evaluation_engine=config.engine,
                    market_start=config.market_start,
                    market_end=config.market_end,
                    llm_provider=config.llm_provider,
                    llm_model=config.llm_model
                )
                
                # Pass the log_queue to the manager
                manager.dispatch_tasks(log_queue=log_queue)
                
                # RUN IN PARALLEL!
                manager.run_swarm(parallel=True)
                
                logger.info("Swarm execution completed successfully.", role="System")
            except Exception as e:
                logger.error(f"Swarm failure: {str(e)}", role="Critical")
                logger.error(traceback.format_exc())
            finally:
                state.is_running = False
                log_queue.put(None) # Stop listener
                
        background_tasks.add_task(run_swarm_logic)
        return {"status": "started"}
    except Exception as e:
        state.is_running = False
        return {"status": "error", "message": f"API Error: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.sockets.append(websocket)
    await websocket.send_json({"type": "log", "level": "INFO", "message": "WebSocket Connected", "timestamp": "Now", "role": "System"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.sockets.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
