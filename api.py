from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import re
import sqlite3
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from core import manual_runner  # noqa: F401  (import-for-side-effect)
from core.runtime import new_run_id
from core.wiki import _parse_frontmatter as parse_wiki_frontmatter
from manager import PortfolioManager


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_\-]+)\]\]")
DB_PATH = Path("results/alpha_miner.db")
SWARM_RUN_DIR = Path("results/swarm_runs")
FRONTEND_DIST_CANDIDATES = (
    Path("frontend_dist"),
    Path("frontend/dist"),
)
MAX_CONCURRENT_SWARMS = int(os.getenv("AIMINER_MAX_CONCURRENT_SWARMS", "2"))
LOG_PAGE_LIMIT_DEFAULT = 100
LOG_PAGE_LIMIT_MAX = 500
LIST_PAGE_LIMIT_DEFAULT = 50
LIST_PAGE_LIMIT_MAX = 200
AUTH_DISABLED = os.getenv("AIMINER_DISABLE_AUTH", "").lower() in {"1", "true", "yes"}
AUTH_TOKEN = os.getenv("AIMINER_AUTH_TOKEN")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "AIMINER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
HTTP_BEARER = HTTPBearer(auto_error=False)


app = FastAPI(title="AIMiner Alpha Workstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


def _ensure_runtime_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SWARM_RUN_DIR.mkdir(parents=True, exist_ok=True)


def _safe_segment(value: str) -> str:
    if not value or not SAFE_ID_RE.match(value):
        raise HTTPException(status_code=400, detail="invalid identifier")
    return value


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _json_dumps(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


_ALPHA_POOL_OPTIONAL_COLUMNS: Dict[str, str] = {
    "selection_score": "REAL",
    "best_strategy_id": "TEXT",
    "best_strategy_metrics_json": "TEXT",
    "execution_style": "TEXT",
}


def _ensure_alpha_pool_schema(conn: sqlite3.Connection) -> None:
    """Idempotent ALTER TABLE so reads can rely on the extended columns."""
    try:
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(alpha_pool)").fetchall()
        }
    except sqlite3.OperationalError:
        return  # table not created yet
    if not existing:
        return
    for column, sql_type in _ALPHA_POOL_OPTIONAL_COLUMNS.items():
        if column in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE alpha_pool ADD COLUMN {column} {sql_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _list_limit(value: int, maximum: int) -> int:
    return max(1, min(value, maximum))


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_json_dumps(payload) + "\n")


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_frontend_dist_dir() -> Optional[Path]:
    for candidate in FRONTEND_DIST_CANDIDATES:
        if (candidate / "index.html").exists():
            return candidate
    for candidate in FRONTEND_DIST_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _frontend_index_path() -> Optional[Path]:
    frontend_dir = _resolve_frontend_dist_dir()
    if not frontend_dir:
        return None
    index_path = frontend_dir / "index.html"
    return index_path if index_path.exists() else None


def _load_jsonl_slice(
    path: Path,
    offset: int = 0,
    limit: int = LOG_PAGE_LIMIT_DEFAULT,
    tail: bool = False,
) -> Dict[str, Any]:
    if not path.exists():
        return {"items": [], "total": 0, "offset": offset, "next_offset": offset}
    limit = _list_limit(limit, LOG_PAGE_LIMIT_MAX)
    items: List[Dict[str, Any]] = []
    all_lines = path.read_text(encoding="utf-8").splitlines()
    total = len(all_lines)
    start = max(0, total - limit) if tail else max(0, offset)
    end = min(total, start + limit)
    for line in all_lines[start:end]:
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {
        "items": items,
        "total": total,
        "offset": start,
        "next_offset": end,
    }


def _manifest_path(run_id: str) -> Path:
    return SWARM_RUN_DIR / f"{run_id}.json"


def _log_path(run_id: str) -> Path:
    return SWARM_RUN_DIR / f"{run_id}.jsonl"


def _count_rows(table: str, column: str, value: str) -> int:
    if not DB_PATH.exists():
        return 0
    try:
        with _db_connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM {table} WHERE {column}=?",
                (value,),
            ).fetchone()
            return int(row["c"]) if row else 0
    except sqlite3.OperationalError:
        return 0


def _factor_summary_for_run(run_id: str) -> Dict[str, int]:
    return {
        "factor_count": _count_rows("alpha_pool", "run_id", run_id),
        "strategy_count": _count_rows("strategy_backtests", "run_id", run_id),
    }


class RunState:
    def __init__(
        self,
        run_id: str,
        process: multiprocessing.Process,
        queue: Any,
        listener_thread: threading.Thread,
        config: Dict[str, Any],
        status: str = "running",
    ):
        self.run_id = run_id
        self.process = process
        self.queue = queue
        self.listener_thread = listener_thread
        self.config = config
        self.status = status

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None


class GlobalState:
    def __init__(self):
        self.sockets: List[WebSocket] = []
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.runs: Dict[str, RunState] = {}
        self.lock = threading.Lock()

    def active_run_ids(self) -> List[str]:
        with self.lock:
            return sorted(
                [
                    run_id
                    for run_id, run_state in self.runs.items()
                    if run_state.process and run_state.process.is_alive()
                ]
            )

    def running_count(self) -> int:
        return len(self.active_run_ids())


state = GlobalState()


class Actor(BaseModel):
    identity: str


def _require_actor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTP_BEARER),
    request: Request = None,
) -> Actor:
    if AUTH_DISABLED:
        return Actor(identity="auth-disabled")
    provided = None
    if credentials and credentials.scheme.lower() == "bearer":
        provided = credentials.credentials
    if request and not provided:
        provided = request.headers.get("X-API-Key")
    if not AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AIMINER_AUTH_TOKEN is not configured",
        )
    if not provided or provided != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        )
    return Actor(identity="bearer")


def _audit(actor: Actor, action: str, target: str, extra: Optional[Dict[str, Any]] = None) -> None:
    payload = {
        "timestamp": _now_iso(),
        "actor": actor.identity,
        "action": action,
        "target": target,
        "extra": extra or {},
    }
    logger.bind(role="Audit").info(_json_dumps(payload))


async def broadcast(message: Dict[str, Any]) -> None:
    dead: List[WebSocket] = []
    for socket in state.sockets:
        try:
            await socket.send_json(message)
        except Exception:
            dead.append(socket)
    for socket in dead:
        try:
            state.sockets.remove(socket)
        except ValueError:
            pass


def _emit_event(message: Dict[str, Any]) -> None:
    if state.loop:
        state.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast(message))
        )


def _write_run_manifest(run_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    path = _manifest_path(run_id)
    current = _load_json(path)
    current.update(patch)
    current.setdefault("run_id", run_id)
    current.setdefault("log_path", str(_log_path(run_id)))
    current["result_counts"] = _factor_summary_for_run(run_id)
    path.write_text(_json_dumps(current), encoding="utf-8")
    return current


def _load_run_manifest(run_id: str) -> Dict[str, Any]:
    manifest = _load_json(_manifest_path(run_id))
    if not manifest:
        raise HTTPException(404, "run not found")
    manifest.setdefault("run_id", run_id)
    manifest.setdefault("log_path", str(_log_path(run_id)))
    manifest["result_counts"] = _factor_summary_for_run(run_id)
    return manifest


def _list_run_manifests(offset: int = 0, limit: int = LIST_PAGE_LIMIT_DEFAULT, status_filter: Optional[str] = None) -> Dict[str, Any]:
    manifests: List[Dict[str, Any]] = []
    if SWARM_RUN_DIR.exists():
        for path in sorted(SWARM_RUN_DIR.glob("run_*.json")):
            manifest = _load_json(path)
            if not manifest:
                continue
            run_id = manifest.get("run_id") or path.stem
            manifest["run_id"] = run_id
            manifest["result_counts"] = _factor_summary_for_run(run_id)
            if status_filter and manifest.get("status") != status_filter:
                continue
            manifests.append(manifest)
    manifests.sort(
        key=lambda item: item.get("started_at") or item.get("created_at") or "",
        reverse=True,
    )
    start = max(0, offset)
    page_limit = _list_limit(limit, LIST_PAGE_LIMIT_MAX)
    end = min(len(manifests), start + page_limit)
    return {
        "items": manifests[start:end],
        "total": len(manifests),
        "offset": start,
        "next_offset": end,
    }


def _register_run(
    run_id: str,
    process: multiprocessing.Process,
    queue: Any,
    listener_thread: threading.Thread,
    config: Dict[str, Any],
    status: str = "running",
) -> None:
    state.runs[run_id] = RunState(
        run_id=run_id,
        process=process,
        queue=queue,
        listener_thread=listener_thread,
        config=config,
        status=status,
    )


def _cleanup_run(run_id: str) -> None:
    with state.lock:
        state.runs.pop(run_id, None)


def _stop_process_tree(pid: Optional[int]) -> None:
    if not pid:
        return
    try:
        parent = psutil.Process(pid)
    except psutil.Error:
        return
    children = parent.children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except psutil.Error:
            continue
    for child in children:
        try:
            child.wait(timeout=3)
        except psutil.Error:
            continue
        except psutil.TimeoutExpired:
            try:
                child.kill()
            except psutil.Error:
                pass
    try:
        parent.terminate()
        parent.wait(timeout=3)
    except psutil.TimeoutExpired:
        try:
            parent.kill()
        except psutil.Error:
            pass
    except psutil.Error:
        pass


def _listen_run_queue(run_id: str, queue: Any) -> None:
    log_path = _log_path(run_id)
    while True:
        try:
            record = queue.get()
        except Exception:
            break
        if record is None:
            break
        record.setdefault("run_id", run_id)
        _append_jsonl(log_path, record)
        if record.get("type") == "status":
            patch = {
                "status": record.get("status"),
                "ended_at": record.get("ended_at"),
                "failure_reason": record.get("failure_reason"),
            }
            _write_run_manifest(run_id, patch)
        elif record.get("type") == "summary":
            _write_run_manifest(
                run_id,
                {
                    "result_counts": {
                        "factor_count": int(record.get("factor_count") or 0),
                        "strategy_count": int(record.get("strategy_count") or 0),
                    }
                },
            )
        _emit_event(record)


def _swarm_process_target(run_id: str, config: Dict[str, Any], queue: Any) -> None:
    def queue_log(level: str, message: str, role: str, agent_id: Optional[str] = None) -> None:
        queue.put(
            {
                "type": "log",
                "run_id": run_id,
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": role,
                "agent_id": agent_id,
            }
        )

    def sink(log_message) -> None:
        record = log_message.record
        extra = record.get("extra", {})
        queue_log(
            record["level"].name,
            record["message"],
            extra.get("role", "System"),
            extra.get("agent_id"),
        )

    logger.remove()
    logger.add(sink, level="INFO")
    queue.put(
        {
            "type": "status",
            "run_id": run_id,
            "event": "started",
            "status": "running",
            "started_at": _now_iso(),
        }
    )
    try:
        manager = PortfolioManager(
            roles=config["roles"],
            run_id=run_id,
            max_iterations=config["iterations"],
            evaluation_mode=config["mode"],
            data_backend=config["data_backend"],
            evaluation_engine=config["engine"],
            llm_provider=config.get("llm_provider"),
            llm_model=config.get("llm_model"),
            llm_base_url=config.get("llm_base_url"),
            embedding_provider=config.get("embedding_provider"),
            market_mode=config.get("market_mode"),
            market_profile=config.get("market_profile"),
            market_profiles=config.get("market_profiles"),
            local_data_path=config.get("local_data_path"),
            local_data_layout=config.get("local_data_layout"),
            market_start=config.get("market_start"),
            market_end=config.get("market_end"),
        )
        manager.run_swarm(parallel=bool(config.get("parallel")), log_queue=queue)
        queue.put(
            {
                "type": "summary",
                "run_id": run_id,
                "factor_count": len(manager.alpha_pool),
                "strategy_count": len(manager.strategy_pool),
            }
        )
        queue.put(
            {
                "type": "status",
                "run_id": run_id,
                "event": "completed",
                "status": "completed",
                "ended_at": _now_iso(),
            }
        )
    except Exception as exc:
        queue.put(
            {
                "type": "log",
                "run_id": run_id,
                "level": "ERROR",
                "message": f"Swarm failure: {exc}",
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": "System",
            }
        )
        queue.put(
            {
                "type": "log",
                "run_id": run_id,
                "level": "ERROR",
                "message": traceback.format_exc(),
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": "System",
            }
        )
        queue.put(
            {
                "type": "status",
                "run_id": run_id,
                "event": "failed",
                "status": "failed",
                "ended_at": _now_iso(),
                "failure_reason": str(exc),
            }
        )
    finally:
        queue.put(None)


def _wait_run_process(run_id: str, process: multiprocessing.Process, queue: Any) -> None:
    process.join()
    try:
        queue.put(None)
    except Exception:
        pass
    _cleanup_run(run_id)


def _paginate_rows(rows: list[sqlite3.Row], offset: int, limit: int) -> Dict[str, Any]:
    start = max(0, offset)
    page_limit = _list_limit(limit, LIST_PAGE_LIMIT_MAX)
    end = min(len(rows), start + page_limit)
    return {
        "items": [dict(row) for row in rows[start:end]],
        "total": len(rows),
        "offset": start,
        "next_offset": end,
    }


def _row_to_factor_detail(row: sqlite3.Row) -> Dict[str, Any]:
    payload = dict(row)
    for column in ("metrics_json", "returns_json", "best_strategy_metrics_json"):
        raw = payload.pop(column, None)
        target = {
            "metrics_json": "metrics",
            "returns_json": "returns",
            "best_strategy_metrics_json": "best_strategy_metrics",
        }[column]
        if not raw:
            payload[target] = {}
            continue
        try:
            payload[target] = json.loads(raw)
        except Exception:
            payload[target] = {}
    is_effective = payload.get("is_effective")
    if is_effective is not None:
        payload["is_effective"] = bool(is_effective)
    factor_id = payload.get("id")
    chart_file = Path(f"results/charts/{factor_id}_curve.png")
    report_file = Path(f"results/reports/{factor_id}.md")
    payload["chart_url"] = f"/api/charts/{factor_id}" if chart_file.exists() else None
    payload["report_url"] = f"/api/reports/{factor_id}" if report_file.exists() else None
    return payload


def _row_to_strategy_detail(row: sqlite3.Row) -> Dict[str, Any]:
    payload = dict(row)
    json_columns = {
        "expression_json": "expression_payload",
        "strategy_config_json": "strategy_config",
        "metrics_json": "metrics",
        "daily_returns_json": "daily_returns",
        "positions_json": "positions",
        "trade_stats_json": "trade_stats",
        "chart_paths_json": "chart_paths",
    }
    for source, target in json_columns.items():
        raw = payload.pop(source, None)
        try:
            payload[target] = json.loads(raw) if raw else {}
        except Exception:
            payload[target] = {}
    payload["expression"] = payload.get("expression_payload", {}).get("expression")
    chart_paths = payload.get("chart_paths", {})
    payload["chart_urls"] = {
        kind: f"/api/strategies/{payload['strategy_id']}/charts/{kind}"
        for kind in ("equity", "turnover")
        if chart_paths.get(kind)
    }
    return payload


def _load_wiki_pages() -> Dict[str, Dict[str, Any]]:
    pages: Dict[str, Dict[str, Any]] = {}
    root = Path("data/wiki_vault")
    if not root.exists():
        return pages
    exclude = {"index.md", "log.md"}
    for path in root.glob("*.md"):
        if path.name in exclude:
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = parse_wiki_frontmatter(text)
        related = meta.get("related") or []
        if not isinstance(related, list):
            related = []
        pages[path.stem] = {
            "slug": path.stem,
            "title": meta.get("title") or path.stem.replace("_", " "),
            "type": meta.get("type") or "factor_card",
            "status": meta.get("status") or "",
            "updated": meta.get("updated") or "",
            "tags": meta.get("tags") or [],
            "related": related,
            "wikilinks": sorted(set(WIKILINK_RE.findall(body))),
        }
    return pages


def _build_wiki_graph() -> Dict[str, Any]:
    pages = _load_wiki_pages()
    degree_map: Dict[str, int] = {slug: 0 for slug in pages}
    edges_seen = set()
    edges: List[Dict[str, str]] = []
    for slug, page in pages.items():
        for target in page["related"]:
            if target not in pages:
                continue
            key = (slug, target, "related")
            if key not in edges_seen:
                edges_seen.add(key)
                edges.append({"source": slug, "target": target, "kind": "related"})
                degree_map[slug] += 1
                degree_map[target] += 1
        for target in page["wikilinks"]:
            if target not in pages:
                continue
            key = (slug, target, "wikilink")
            if key not in edges_seen:
                edges_seen.add(key)
                edges.append({"source": slug, "target": target, "kind": "wikilink"})
                degree_map[slug] += 1
                degree_map[target] += 1
    return {
        "nodes": [
            {
                "id": slug,
                "slug": slug,
                "title": page["title"],
                "type": page["type"],
                "status": page["status"],
                "updated": page["updated"],
                "tags": page["tags"],
                "degree": degree_map[slug],
            }
            for slug, page in sorted(pages.items())
        ],
        "edges": edges,
    }


class SwarmConfig(BaseModel):
    iterations: int = 2
    mode: str = "ricequant"
    data_backend: str = "ricequant"
    engine: str = "polars"
    roles: List[str]
    market_start: str = "2017-01-01"
    market_end: str = "2020-10-31"
    llm_provider: str = "kimi"
    llm_model: str = "kimi-k2-turbo-preview"
    llm_base_url: Optional[str] = None
    embedding_provider: Optional[str] = None
    market_mode: str = "single"
    market_profile: str = "cn_stock"
    market_profiles: List[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"
    parallel: bool = True


class BacktestRequest(BaseModel):
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
    skip_validation: bool = False
    label: Optional[str] = None
    data_backend: str = "ricequant"
    market_profile: str = "cn_stock"
    market_mode: str = "single"
    market_profiles: List[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"


class StrategyRunRequest(BaseModel):
    expression: str
    strategy_config: Dict[str, Any]
    data_backend: str = "ricequant"
    market_profile: str = "cn_stock"
    market_mode: str = "single"
    market_profiles: List[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"


@app.on_event("startup")
async def startup_event() -> None:
    _ensure_runtime_dirs()
    if DB_PATH.exists():
        with _db_connect() as conn:
            _ensure_alpha_pool_schema(conn)
    state.loop = asyncio.get_running_loop()


@app.get("/", response_model=None)
def read_index():
    index_path = _frontend_index_path()
    if index_path:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return PlainTextResponse(
        "AIMiner API server.\nFrontend assets are not built.\n",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "auth_disabled": AUTH_DISABLED,
        "active_run_ids": state.active_run_ids(),
    }


@app.get("/api/results")
def get_results(
    run_id: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
) -> Dict[str, Any]:
    if run_id:
        run_id = _safe_segment(run_id)
    if not DB_PATH.exists():
        return {"items": [], "total": 0, "offset": offset, "next_offset": offset}
    select_cols = (
        "id, role, hypothesis, code, ic, rank_ic, is_effective, "
        "perf_metric, selection_score, best_strategy_id, report_path, timestamp, run_id"
    )
    with _db_connect() as conn:
        _ensure_alpha_pool_schema(conn)
        if run_id:
            rows = conn.execute(
                f"SELECT {select_cols} FROM alpha_pool WHERE run_id=? ORDER BY timestamp DESC",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {select_cols} FROM alpha_pool ORDER BY timestamp DESC"
            ).fetchall()
    return _paginate_rows(list(rows), offset, limit)


@app.get("/api/factors/{factor_id}")
def get_factor_detail(factor_id: str) -> Dict[str, Any]:
    factor_id = _safe_segment(factor_id)
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        row = conn.execute("SELECT * FROM alpha_pool WHERE id=?", (factor_id,)).fetchone()
        strategy_row = None
        if row and "best_strategy_id" in row.keys() and row["best_strategy_id"]:
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


@app.get("/api/charts/{factor_id}")
def get_chart(factor_id: str) -> FileResponse:
    factor_id = _safe_segment(factor_id)
    path = Path(f"results/charts/{factor_id}_curve.png")
    if not path.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(path), media_type="image/png")


@app.get("/api/reports/{factor_id}", response_class=PlainTextResponse)
def get_report(factor_id: str) -> PlainTextResponse:
    factor_id = _safe_segment(factor_id)
    path = Path(f"results/reports/{factor_id}.md")
    if not path.exists():
        raise HTTPException(404, "report not found")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/wiki/index")
def wiki_index(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
) -> Dict[str, Any]:
    pages = _load_wiki_pages()
    rows = [
        {
            "slug": slug,
            "title": page["title"],
            "updated": page["updated"],
            "type": page["type"],
            "status": page["status"],
        }
        for slug, page in pages.items()
    ]
    rows.sort(key=lambda item: item.get("updated") or "", reverse=True)
    total = len(rows)
    start = max(0, offset)
    page_limit = _list_limit(limit, LIST_PAGE_LIMIT_MAX)
    end = min(total, start + page_limit)
    return {
        "items": rows[start:end],
        "total": total,
        "offset": start,
        "next_offset": end,
    }


@app.get("/api/wiki/page/{slug}", response_class=PlainTextResponse)
def wiki_page(slug: str) -> PlainTextResponse:
    slug = _safe_segment(slug)
    path = Path("data/wiki_vault") / f"{slug}.md"
    if not path.exists() or path.name in {"index.md", "log.md"}:
        raise HTTPException(404, "wiki page not found")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/wiki/graph")
def wiki_graph() -> Dict[str, Any]:
    return _build_wiki_graph()


class ResetRequest(BaseModel):
    scopes: List[str] = Field(
        default_factory=lambda: ["pool"],
        description="One or more of: pool, memory, rag, runs, all.",
    )
    confirm: bool = Field(
        default=False,
        description="When false, returns the dry-run plan without moving anything.",
    )
    reset_token: Optional[str] = Field(
        default=None,
        description=(
            "Required when confirm=true: must equal AIMINER_RESET_TOKEN env var. "
            "Defends against accidental destructive POSTs by reusing-API-token clients."
        ),
    )


@app.post("/api/admin/reset")
def admin_reset(
    req: ResetRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    """Wipe mining artifacts. Always reversible (moves into results/.trash/<ts>/)."""
    from scripts.reset_workspace import build_plan, execute_plan, render_plan

    if req.confirm:
        expected = os.getenv("AIMINER_RESET_TOKEN")
        if not expected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AIMINER_RESET_TOKEN is not configured on the server",
            )
        if not req.reset_token or req.reset_token != expected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="reset_token mismatch",
            )

    try:
        plan = build_plan(req.scopes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _audit(actor, "admin.reset", ",".join(plan.scopes), {"confirm": req.confirm})
    summary = execute_plan(plan, confirm=req.confirm)
    summary["plan_text"] = render_plan(plan)
    return summary


@app.post("/api/wiki/lint")
def wiki_lint(
    stale_days: int = 30,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    from core.wiki import LLMWiki

    _audit(actor, "wiki.lint", "wiki", {"stale_days": stale_days})
    try:
        wiki = LLMWiki()
        return wiki.lint(stale_days=stale_days)
    except Exception as exc:
        raise HTTPException(500, f"lint failed: {exc}")


@app.post("/api/wiki/migrate")
def wiki_migrate(
    dry_run: bool = False,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    from core.wiki import LLMWiki

    _audit(actor, "wiki.migrate", "wiki", {"dry_run": dry_run})
    try:
        wiki = LLMWiki()
        return wiki.migrate_legacy_pages(dry_run=dry_run)
    except Exception as exc:
        raise HTTPException(500, f"migrate failed: {exc}")


@app.post("/api/backtest/validate")
def backtest_validate(
    req: BacktestRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "backtest.validate", "manual", {"label": req.label})
    ok, msg = manual_runner.validate_expression(req.expression)
    return {"ok": bool(ok), "message": msg}


@app.post("/api/backtest/run")
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
            req.data_backend,
            req.market_profile,
            req.market_mode,
            req.market_profiles,
            req.local_data_path,
            req.local_data_layout,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(f"[Manual BT] Unhandled error: {exc}\n{traceback.format_exc()}")
        raise HTTPException(500, "backtest failed")
    result["cached"] = False
    return result


@app.get("/api/backtest/history")
def backtest_history(
    actor: Actor = Depends(_require_actor),
) -> List[Dict[str, Any]]:
    _audit(actor, "backtest.history", "manual")
    return manual_runner.list_jobs(include_returns=False)


@app.get("/api/backtest/{job_id}")
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


@app.delete("/api/backtest/{job_id}")
def backtest_delete(
    job_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    job_id = _safe_segment(job_id)
    _audit(actor, "backtest.delete", job_id)
    if not manual_runner.delete_job(job_id):
        raise HTTPException(404, "backtest job not found")
    return {"status": "deleted", "job_id": job_id}


@app.post("/api/strategy/run")
async def strategy_run(
    req: StrategyRunRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "strategy.run", "manual")
    try:
        result = await asyncio.to_thread(
            manual_runner.run_manual_strategy_backtest,
            req.expression,
            req.strategy_config,
            req.data_backend,
            req.market_profile,
            req.market_mode,
            req.market_profiles,
            req.local_data_path,
            req.local_data_layout,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(f"[Strategy BT] Unhandled error: {exc}\n{traceback.format_exc()}")
        raise HTTPException(500, "strategy backtest failed")
    return result


@app.get("/api/strategy/history")
def strategy_history(
    actor: Actor = Depends(_require_actor),
) -> List[Dict[str, Any]]:
    _audit(actor, "strategy.history", "manual")
    return manual_runner.list_strategy_jobs(include_returns=False)


@app.get("/api/strategies")
def get_strategies(
    run_id: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
) -> Dict[str, Any]:
    if run_id:
        run_id = _safe_segment(run_id)
    if not DB_PATH.exists():
        return {"items": [], "total": 0, "offset": offset, "next_offset": offset}
    with _db_connect() as conn:
        try:
            if run_id:
                rows = conn.execute(
                    """
                    SELECT strategy_id, label, strategy_mode, metrics_json, market, engine,
                           ran_at, run_id, source_factor_id, candidate_rank, selection_score, is_primary
                    FROM strategy_backtests
                    WHERE run_id=?
                    ORDER BY ran_at DESC
                    """,
                    (run_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT strategy_id, label, strategy_mode, metrics_json, market, engine,
                           ran_at, run_id, source_factor_id, candidate_rank, selection_score, is_primary
                    FROM strategy_backtests
                    ORDER BY ran_at DESC
                    """
                ).fetchall()
        except sqlite3.OperationalError:
            if run_id:
                rows = conn.execute(
                    """
                    SELECT strategy_id, label, strategy_mode, metrics_json, market, engine,
                           ran_at, run_id, source_factor_id, NULL AS candidate_rank, NULL AS selection_score, NULL AS is_primary
                    FROM strategy_backtests
                    WHERE run_id=?
                    ORDER BY ran_at DESC
                    """,
                    (run_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT strategy_id, label, strategy_mode, metrics_json, market, engine,
                           ran_at, run_id, source_factor_id, NULL AS candidate_rank, NULL AS selection_score, NULL AS is_primary
                    FROM strategy_backtests
                    ORDER BY ran_at DESC
                    """
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


@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> Dict[str, Any]:
    strategy_id = _safe_segment(strategy_id)
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM strategy_backtests WHERE strategy_id=?",
            (strategy_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "strategy not found")
    return _row_to_strategy_detail(row)


@app.delete("/api/strategy/{strategy_id}")
def delete_strategy(
    strategy_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    strategy_id = _safe_segment(strategy_id)
    _audit(actor, "strategy.delete", strategy_id)
    if not manual_runner.delete_strategy_job(strategy_id):
        raise HTTPException(404, "strategy backtest not found")
    if DB_PATH.exists():
        with _db_connect() as conn:
            conn.execute(
                "DELETE FROM strategy_backtests WHERE strategy_id=?",
                (strategy_id,),
            )
            conn.commit()
    return {"status": "deleted", "strategy_id": strategy_id}


@app.get("/api/strategies/{strategy_id}/charts/{kind}")
def get_strategy_chart(strategy_id: str, kind: str) -> FileResponse:
    strategy_id = _safe_segment(strategy_id)
    if kind not in {"equity", "turnover"}:
        raise HTTPException(400, "invalid chart kind")
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        row = conn.execute(
            "SELECT chart_paths_json FROM strategy_backtests WHERE strategy_id=?",
            (strategy_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "strategy not found")
    chart_paths = json.loads(row["chart_paths_json"] or "{}")
    path = chart_paths.get(kind)
    if not path or not Path(path).exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(path), media_type="image/png")


@app.get("/api/swarm/status")
def swarm_status(actor: Actor = Depends(_require_actor)) -> Dict[str, Any]:
    _audit(actor, "swarm.status", "global")
    return {
        "running_count": state.running_count(),
        "active_run_ids": state.active_run_ids(),
        "max_concurrent": MAX_CONCURRENT_SWARMS,
    }


@app.get("/api/swarm/runs")
def list_swarm_runs(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "swarm.list", "global", {"status": status_filter})
    return _list_run_manifests(offset=offset, limit=limit, status_filter=status_filter)


@app.post("/api/swarm/runs")
def start_swarm(
    config: SwarmConfig,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "swarm.start", "global", {"iterations": config.iterations})
    with state.lock:
        if state.running_count() >= MAX_CONCURRENT_SWARMS:
            raise HTTPException(409, "concurrency limit reached")
        run_id = new_run_id()
        config_payload = config.model_dump()
        _write_run_manifest(
            run_id,
            {
                "run_id": run_id,
                "status": "starting",
                "created_at": _now_iso(),
                "started_at": _now_iso(),
                "ended_at": None,
                "parallel": bool(config.parallel),
                "config": config_payload,
                "result_counts": {"factor_count": 0, "strategy_count": 0},
            },
        )
        queue = multiprocessing.Queue()
        listener_thread = threading.Thread(
            target=_listen_run_queue,
            args=(run_id, queue),
            daemon=True,
        )
        listener_thread.start()
        process = multiprocessing.Process(
            target=_swarm_process_target,
            args=(run_id, config_payload, queue),
            daemon=False,
        )
        process.start()
        _write_run_manifest(run_id, {"process_pid": process.pid, "status": "running"})
        _register_run(run_id, process, queue, listener_thread, config_payload)
    threading.Thread(
        target=_wait_run_process,
        args=(run_id, process, queue),
        daemon=True,
    ).start()
    event = {
        "type": "status",
        "run_id": run_id,
        "event": "started",
        "status": "running",
        "started_at": _load_json(_manifest_path(run_id)).get("started_at"),
        "ended_at": None,
    }
    _append_jsonl(_log_path(run_id), event)
    _emit_event(event)
    return {"status": "started", "run_id": run_id}


@app.get("/api/swarm/runs/{run_id}")
def get_swarm_run(
    run_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    run_id = _safe_segment(run_id)
    _audit(actor, "swarm.get", run_id)
    manifest = _load_run_manifest(run_id)
    with state.lock:
        run_state = state.runs.get(run_id)
    manifest["is_active"] = bool(run_state and run_state.process.is_alive())
    return manifest


@app.get("/api/swarm/runs/{run_id}/logs")
def get_swarm_run_logs(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LOG_PAGE_LIMIT_DEFAULT, ge=1),
    tail: bool = Query(default=False),
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    run_id = _safe_segment(run_id)
    _audit(actor, "swarm.logs", run_id, {"offset": offset, "limit": limit, "tail": tail})
    if not _manifest_path(run_id).exists():
        raise HTTPException(404, "run not found")
    return _load_jsonl_slice(_log_path(run_id), offset=offset, limit=limit, tail=tail)


@app.post("/api/swarm/runs/{run_id}/stop")
def stop_swarm(
    run_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    run_id = _safe_segment(run_id)
    _audit(actor, "swarm.stop", run_id)
    with state.lock:
        run_state = state.runs.get(run_id)
    manifest = _load_run_manifest(run_id)
    current_status = manifest.get("status")
    if current_status in {"completed", "failed", "stopped"}:
        return {"status": current_status, "run_id": run_id}
    if not run_state:
        raise HTTPException(404, "run not active")
    _stop_process_tree(run_state.pid)
    ended_at = _now_iso()
    _write_run_manifest(
        run_id,
        {
            "status": "stopped",
            "ended_at": ended_at,
        },
    )
    event = {
        "type": "status",
        "run_id": run_id,
        "event": "stopped",
        "status": "stopped",
        "started_at": manifest.get("started_at"),
        "ended_at": ended_at,
    }
    _append_jsonl(_log_path(run_id), event)
    _emit_event(event)
    return {"status": "stopped", "run_id": run_id}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not AUTH_DISABLED:
        if not AUTH_TOKEN:
            await websocket.close(code=1011)
            return
        if token != AUTH_TOKEN:
            await websocket.close(code=1008)
            return
    await websocket.accept()
    state.sockets.append(websocket)
    await websocket.send_json(
        {
            "type": "status",
            "event": "connected",
            "status": "ok",
            "active_run_ids": state.active_run_ids(),
            "max_concurrent": MAX_CONCURRENT_SWARMS,
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            state.sockets.remove(websocket)
        except ValueError:
            pass


FRONTEND_DIST_DIR = _resolve_frontend_dist_dir()

if FRONTEND_DIST_DIR:
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/{full_path:path}", response_model=None)
def frontend_fallback(full_path: str):
    if full_path.startswith("api") or full_path.startswith("ws"):
        raise HTTPException(404, "not found")
    index_path = _frontend_index_path()
    if index_path:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return PlainTextResponse("frontend not built", status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
