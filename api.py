from __future__ import annotations

import asyncio
import fcntl
import json
import multiprocessing
import os
import queue as queue_module
import re
import sqlite3
import threading
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from core import manual_runner  # noqa: F401  (import-for-side-effect)
from core.runtime import new_run_id
from core.settings import (
    SUPPORTED_DATA_BACKENDS,
    SUPPORTED_EVALUATION_MODES,
    SUPPORTED_LLM_PROVIDERS,
    SUPPORTED_LLM_REASONING_EFFORTS,
    SUPPORTED_LOCAL_DATA_LAYOUTS,
    SUPPORTED_MARKET_MODES,
    SUPPORTED_MARKET_PROFILES,
    build_settings,
)
from core.wiki import _parse_frontmatter as parse_wiki_frontmatter
from manager import PortfolioManager

load_dotenv()


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_\-]+)\]\]")
SETTINGS = build_settings()
DB_PATH = SETTINGS.db_path
SWARM_RUN_DIR = SETTINGS.swarm_run_dir
CHART_DIR = SETTINGS.chart_dir
REPORT_DIR = SETTINGS.report_dir
WIKI_DIR = SETTINGS.wiki_dir
FRONTEND_DIST_CANDIDATES = (
    Path("frontend_dist"),
    Path("frontend/dist"),
)
MAX_CONCURRENT_SWARMS = int(os.getenv("AIMINER_MAX_CONCURRENT_SWARMS", "2"))
SWARM_QUEUE_MAXSIZE = int(os.getenv("AIMINER_SWARM_QUEUE_MAXSIZE", "2000"))
STALE_STARTING_SECONDS = int(os.getenv("AIMINER_STALE_STARTING_SECONDS", "120"))
SWARM_RUN_TIMEOUT_SECONDS = int(os.getenv("AIMINER_SWARM_RUN_TIMEOUT_SECONDS", "3600"))
SWARM_RUN_HEARTBEAT_SECONDS = int(os.getenv("AIMINER_SWARM_RUN_HEARTBEAT_SECONDS", "15"))
MANUAL_BACKTEST_TIMEOUT_SECONDS = int(os.getenv("AIMINER_MANUAL_BACKTEST_TIMEOUT_SECONDS", "600"))
STRATEGY_BACKTEST_TIMEOUT_SECONDS = int(os.getenv("AIMINER_STRATEGY_BACKTEST_TIMEOUT_SECONDS", "900"))
LOG_PAGE_LIMIT_DEFAULT = 100
LOG_PAGE_LIMIT_MAX = 500
LIST_PAGE_LIMIT_DEFAULT = 50
LIST_PAGE_LIMIT_MAX = 200
AUTH_TOKEN = os.getenv("AIMINER_AUTH_TOKEN")
AUTH_DISABLED = os.getenv("AIMINER_DISABLE_AUTH", "").lower() in {"1", "true", "yes"} or not AUTH_TOKEN
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "AIMINER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
HTTP_BEARER = HTTPBearer(auto_error=False)
ACTIVE_RUN_STATUSES = {"starting", "pending", "running"}
FINAL_RUN_STATUSES = {"completed", "failed", "stopped"}
ENGINE_CHOICES = ("pandas", "polars")
_MANIFEST_LOCKS: Dict[str, threading.RLock] = {}
_MANIFEST_LOCKS_GUARD = threading.Lock()


app = FastAPI(title="AIMiner Alpha Workstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
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
    "run_id": "TEXT",
}

_STRATEGY_BACKTEST_OPTIONAL_COLUMNS: Dict[str, str] = {
    "template_name": "TEXT",
    "rationale": "TEXT",
    "run_id": "TEXT",
    "source_factor_id": "TEXT",
    "agent_id": "TEXT",
    "candidate_rank": "INTEGER",
    "selection_score": "REAL",
    "is_primary": "INTEGER",
    "market_profile": "TEXT",
    "data_backend": "TEXT",
}

_ALPHA_POOL_RESULT_COLUMNS = (
    "id",
    "role",
    "hypothesis",
    "code",
    "ic",
    "rank_ic",
    "is_effective",
    "perf_metric",
    "selection_score",
    "best_strategy_id",
    "report_path",
    "timestamp",
    "run_id",
)

_STRATEGY_LIST_COLUMNS = (
    "strategy_id",
    "label",
    "template_name",
    "rationale",
    "strategy_mode",
    "metrics_json",
    "market",
    "engine",
    "ran_at",
    "run_id",
    "source_factor_id",
    "candidate_rank",
    "selection_score",
    "is_primary",
)

_ALPHA_POOL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alpha_pool (
    id TEXT PRIMARY KEY,
    role TEXT,
    hypothesis TEXT,
    code TEXT,
    ic REAL,
    rank_ic REAL,
    report_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metrics_json TEXT,
    returns_json TEXT,
    is_effective INTEGER,
    perf_metric REAL,
    selection_score REAL,
    best_strategy_id TEXT,
    best_strategy_metrics_json TEXT,
    execution_style TEXT,
    run_id TEXT,
    agent_id TEXT,
    iteration INTEGER,
    evaluation_mode TEXT,
    evaluation_engine TEXT,
    data_backend TEXT,
    market_mode TEXT,
    market_profile TEXT,
    llm_provider TEXT,
    llm_model TEXT,
    is_simulated INTEGER
)
"""

_STRATEGY_BACKTESTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS strategy_backtests (
    strategy_id TEXT PRIMARY KEY,
    label TEXT,
    template_name TEXT,
    rationale TEXT,
    run_type TEXT,
    strategy_mode TEXT,
    signal_source TEXT,
    expression_json TEXT,
    strategy_config_json TEXT,
    metrics_json TEXT,
    daily_returns_json TEXT,
    positions_json TEXT,
    trade_stats_json TEXT,
    chart_paths_json TEXT,
    market TEXT,
    engine TEXT,
    ran_at TEXT,
    run_id TEXT,
    source_factor_id TEXT,
    agent_id TEXT,
    candidate_rank INTEGER,
    selection_score REAL,
    is_primary INTEGER,
    market_profile TEXT,
    data_backend TEXT
)
"""


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {
            str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
    except sqlite3.OperationalError as exc:
        logger.warning(f"[schema] failed to inspect {table}: {exc}")
        return set()


def _ensure_optional_columns(
    conn: sqlite3.Connection,
    table: str,
    columns: Dict[str, str],
) -> None:
    existing = _table_columns(conn, table)
    if not existing:
        return
    mutated = False
    for column, sql_type in columns.items():
        if column in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            existing.add(column)
            mutated = True
        except sqlite3.OperationalError as exc:
            logger.warning(f"[schema] failed to add {table}.{column}: {exc}")
    if mutated:
        conn.commit()


def _ensure_alpha_pool_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_ALPHA_POOL_TABLE_SQL)
    _ensure_optional_columns(conn, "alpha_pool", _ALPHA_POOL_OPTIONAL_COLUMNS)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alpha_timestamp ON alpha_pool(timestamp)")
    if "run_id" in _table_columns(conn, "alpha_pool"):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alpha_run_id ON alpha_pool(run_id)")


def _ensure_strategy_backtests_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_STRATEGY_BACKTESTS_TABLE_SQL)
    _ensure_optional_columns(conn, "strategy_backtests", _STRATEGY_BACKTEST_OPTIONAL_COLUMNS)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_ran_at ON strategy_backtests(ran_at)"
    )
    if "run_id" in _table_columns(conn, "strategy_backtests"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_run_id ON strategy_backtests(run_id)"
        )


def _ensure_db_schema(conn: sqlite3.Connection) -> None:
    _ensure_alpha_pool_schema(conn)
    _ensure_strategy_backtests_schema(conn)


def _select_projection(existing: set[str], columns: tuple[str, ...]) -> str:
    return ", ".join(
        column if column in existing else f"NULL AS {column}"
        for column in columns
    )


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def _list_limit(value: int, maximum: int) -> int:
    return max(1, min(value, maximum))


def _empty_page(offset: int, limit: int, maximum: int = LIST_PAGE_LIMIT_MAX) -> Dict[str, Any]:
    start = max(0, offset)
    page_limit = _list_limit(limit, maximum)
    return {"items": [], "total": 0, "offset": start, "limit": page_limit, "next_offset": start}


def _run_manifest_lock(run_id: str) -> threading.RLock:
    with _MANIFEST_LOCKS_GUARD:
        lock = _MANIFEST_LOCKS.get(run_id)
        if lock is None:
            lock = threading.RLock()
            _MANIFEST_LOCKS[run_id] = lock
        return lock


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


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
    limit = _list_limit(limit, LOG_PAGE_LIMIT_MAX)
    if not path.exists():
        return _empty_page(offset, limit, LOG_PAGE_LIMIT_MAX)
    items: List[Dict[str, Any]] = []
    total = 0
    start = max(0, offset)
    if tail:
        window: deque[str] = deque(maxlen=limit)
        with path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                total += 1
                window.append(raw_line)
        start = max(0, total - limit)
        selected_lines = list(window)
    else:
        end = start + limit
        selected_lines = []
        with path.open("r", encoding="utf-8") as fh:
            for line_index, raw_line in enumerate(fh):
                total += 1
                if start <= line_index < end:
                    selected_lines.append(raw_line)
    end = min(total, start + limit)
    for line in selected_lines:
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
        "limit": limit,
        "next_offset": total if tail else end,
    }


def _manifest_path(run_id: str) -> Path:
    return SWARM_RUN_DIR / f"{run_id}.json"


def _manifest_lock_path(run_id: str) -> Path:
    return SWARM_RUN_DIR / f"{run_id}.json.lock"


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
    except sqlite3.OperationalError as exc:
        logger.warning(f"[counts] failed to count {table}.{column} for {value}: {exc}")
        return 0


def _factor_summary_for_run(run_id: str) -> Dict[str, int]:
    return {
        "factor_count": _count_rows("alpha_pool", "run_id", run_id),
        "strategy_count": _count_rows("strategy_backtests", "run_id", run_id),
    }


def _readiness_payload() -> Dict[str, Any]:
    from core.rag import chroma_sqlite_summary, resolve_embedding_model_tag

    model_tag = resolve_embedding_model_tag(SETTINGS.embedding_provider)
    rag = chroma_sqlite_summary(str(SETTINGS.data_path / "chroma_db"), model_tag)
    wiki = chroma_sqlite_summary(str(SETTINGS.data_path / "wiki_db"), model_tag)
    db_ready = DB_PATH.parent.exists()
    ready = bool(db_ready and rag.get("ready") and wiki.get("ready"))
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "db": {
            "path": str(DB_PATH),
            "parent_exists": db_ready,
            "exists": DB_PATH.exists(),
        },
        "embedding": {
            "provider": SETTINGS.embedding_provider,
            "model_tag": model_tag,
        },
        "rag": rag,
        "wiki": wiki,
    }


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _resolve_active_pid(manifest: Dict[str, Any], run_state: Optional["RunState"] = None) -> Optional[int]:
    if run_state and run_state.process:
        try:
            if run_state.process.is_alive():
                return run_state.pid
        except Exception:
            pass

    pid = manifest.get("process_pid")
    create_time = _safe_float(manifest.get("process_create_time"))
    if not pid or create_time is None:
        return None
    if int(pid) == os.getpid():
        return None
    try:
        process = psutil.Process(int(pid))
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return None
        if abs(process.create_time() - create_time) > 0.5:
            return None
    except psutil.Error:
        return None
    return int(pid)


def _is_stale_starting_run(manifest: Dict[str, Any], is_active: bool) -> bool:
    if is_active:
        return False
    if str(manifest.get("status") or "") not in {"starting", "pending"}:
        return False
    started = _parse_iso_datetime(manifest.get("started_at") or manifest.get("created_at"))
    if not started:
        return False
    now = datetime.now(started.tzinfo) if started.tzinfo else datetime.utcnow()
    return (now - started).total_seconds() >= STALE_STARTING_SECONDS


def _normalized_run_status(manifest: Dict[str, Any], is_active: bool) -> str:
    status = str(manifest.get("status") or "")
    if _is_stale_starting_run(manifest, is_active):
        return "failed"
    if status == "stopped" and is_active:
        return "stopping"
    if status == "stopping" and not is_active:
        return "stopped"
    if status in ACTIVE_RUN_STATUSES and manifest.get("process_pid") and not is_active:
        return "stopped"
    return status


def _annotate_run_manifest(
    run_id: str,
    manifest: Dict[str, Any],
    run_state: Optional["RunState"] = None,
    persist: bool = False,
) -> Dict[str, Any]:
    active_pid = _resolve_active_pid(manifest, run_state)
    is_active = active_pid is not None
    normalized_status = _normalized_run_status(manifest, is_active)
    if persist:
        patch: Dict[str, Any] = {}
        stale_starting = _is_stale_starting_run(manifest, is_active)
        if manifest.get("status") != normalized_status:
            patch["status"] = normalized_status
        if normalized_status in FINAL_RUN_STATUSES and not manifest.get("ended_at"):
            patch["ended_at"] = _now_iso()
        elif normalized_status not in FINAL_RUN_STATUSES and manifest.get("ended_at"):
            patch["ended_at"] = None
        if stale_starting and not manifest.get("failure_reason"):
            patch["failure_reason"] = "stale starting run recovered by API"
        if patch:
            manifest = _write_run_manifest(run_id, patch)
    manifest["status"] = normalized_status
    manifest["is_active"] = is_active
    return manifest


def _collect_active_run_ids() -> List[str]:
    run_ids = set()
    with state.lock:
        active_states = dict(state.runs)
    for run_id, run_state in active_states.items():
        try:
            if run_state.process and run_state.process.is_alive():
                run_ids.add(run_id)
        except Exception:
            continue
    if SWARM_RUN_DIR.exists():
        for path in SWARM_RUN_DIR.glob("run_*.json"):
            manifest = _load_json(path)
            if not manifest:
                continue
            run_id = manifest.get("run_id") or path.stem
            if _resolve_active_pid(manifest, active_states.get(run_id)) is not None:
                run_ids.add(run_id)
    return sorted(run_ids)


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
        self.sockets: set[WebSocket] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.runs: Dict[str, RunState] = {}
        # API handlers sometimes call helper methods that also acquire the
        # same state lock; use an RLock so those paths don't self-deadlock.
        self.lock = threading.RLock()

    def active_run_ids(self) -> List[str]:
        return _collect_active_run_ids()

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


def _service_error(exc: Exception, fallback: str) -> HTTPException:
    message = str(exc).strip() or fallback
    if "Disconnected from the remote server" in message:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RiceQuant disconnected from the remote server. Retry later, or switch Data Backend to local/qlib.",
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


async def broadcast(message: Dict[str, Any]) -> None:
    with state.lock:
        sockets = list(state.sockets)
    dead: List[WebSocket] = []
    for socket in sockets:
        try:
            await socket.send_json(message)
        except Exception:
            dead.append(socket)
    if dead:
        with state.lock:
            for socket in dead:
                state.sockets.discard(socket)


def _emit_event(message: Dict[str, Any]) -> None:
    if state.loop:
        state.loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast(message))
        )


def _write_run_manifest(run_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    path = _manifest_path(run_id)
    with _run_manifest_lock(run_id):
        lock_path = _manifest_lock_path(run_id)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                current = _load_json(path)
                current.update(patch)
                current.setdefault("run_id", run_id)
                current.setdefault("log_path", str(_log_path(run_id)))
                current["result_counts"] = _manifest_result_counts(current)
                _atomic_write_text(path, _json_dumps(current))
                return current
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def _load_run_manifest(run_id: str) -> Dict[str, Any]:
    manifest = _load_json(_manifest_path(run_id))
    if not manifest:
        raise HTTPException(404, "run not found")
    manifest.setdefault("run_id", run_id)
    manifest.setdefault("log_path", str(_log_path(run_id)))
    if "result_counts" not in manifest:
        counts = _factor_summary_for_run(run_id)
        manifest["result_counts"] = counts
        _write_run_manifest(run_id, {"result_counts": counts})
    else:
        manifest["result_counts"] = _manifest_result_counts(manifest)
    with state.lock:
        run_state = state.runs.get(run_id)
    return _annotate_run_manifest(run_id, manifest, run_state, persist=True)


def _list_run_manifests(offset: int = 0, limit: int = LIST_PAGE_LIMIT_DEFAULT, status_filter: Optional[str] = None) -> Dict[str, Any]:
    manifests: List[Dict[str, Any]] = []
    with state.lock:
        active_states = dict(state.runs)
    if SWARM_RUN_DIR.exists():
        for path in sorted(SWARM_RUN_DIR.glob("run_*.json")):
            manifest = _load_json(path)
            if not manifest:
                continue
            run_id = manifest.get("run_id") or path.stem
            manifest["run_id"] = run_id
            if "result_counts" not in manifest:
                counts = _factor_summary_for_run(run_id)
                manifest["result_counts"] = counts
                _write_run_manifest(run_id, {"result_counts": counts})
            else:
                manifest["result_counts"] = _manifest_result_counts(manifest)
            manifest = _annotate_run_manifest(run_id, manifest, active_states.get(run_id), persist=True)
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
        "limit": page_limit,
        "next_offset": end,
    }


def _find_run_by_client_key(client_run_key: Optional[str]) -> Optional[str]:
    if not client_run_key or not SWARM_RUN_DIR.exists():
        return None
    for path in sorted(SWARM_RUN_DIR.glob("run_*.json"), reverse=True):
        manifest = _load_json(path)
        config = manifest.get("config") if isinstance(manifest, dict) else {}
        if isinstance(config, dict) and config.get("client_run_key") == client_run_key:
            return str(manifest.get("run_id") or path.stem)
    return None


def _register_run(
    run_id: str,
    process: multiprocessing.Process,
    queue: Any,
    listener_thread: threading.Thread,
    config: Dict[str, Any],
    status: str = "running",
) -> None:
    with state.lock:
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


def _manifest_result_counts(manifest: Dict[str, Any]) -> Dict[str, int]:
    raw = manifest.get("result_counts")
    if not isinstance(raw, dict):
        raw = {}
    return {
        "factor_count": int(raw.get("factor_count") or 0),
        "strategy_count": int(raw.get("strategy_count") or 0),
    }


def _queue_put(queue: Any, payload: Any, *, required: bool = False) -> None:
    try:
        queue.put(payload, timeout=1)
        return
    except queue_module.Full:
        if not required and isinstance(payload, dict) and payload.get("type") == "log":
            logger.warning("[swarm] log queue full; dropping log record")
            return
        try:
            queue.put(payload, timeout=5)
            return
        except Exception as exc:
            logger.warning(f"[swarm] failed to enqueue required event: {exc}")
    except Exception as exc:
        logger.warning(f"[swarm] queue put failed: {exc}")


def _listen_run_queue(run_id: str, queue: Any) -> None:
    log_path = _log_path(run_id)
    idle_polls = 0
    while True:
        try:
            record = queue.get(timeout=1)
            idle_polls = 0
        except queue_module.Empty:
            idle_polls += 1
            if idle_polls >= 3:
                manifest = _load_json(_manifest_path(run_id))
                with state.lock:
                    run_state = state.runs.get(run_id)
                if (
                    manifest
                    and manifest.get("status") in FINAL_RUN_STATUSES
                    and _resolve_active_pid(manifest, run_state) is None
                ):
                    break
            continue
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
        _queue_put(
            queue,
            {
                "type": "log",
                "run_id": run_id,
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": role,
                "agent_id": agent_id,
            },
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
    _queue_put(
        queue,
        {
            "type": "status",
            "run_id": run_id,
            "event": "started",
            "status": "running",
            "started_at": _now_iso(),
        },
        required=True,
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
            llm_reasoning_effort=config.get("llm_reasoning_effort"),
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
        _queue_put(
            queue,
            {
                "type": "summary",
                "run_id": run_id,
                "factor_count": len(manager.alpha_pool),
                "strategy_count": len(manager.strategy_pool),
            },
            required=True,
        )
        _queue_put(
            queue,
            {
                "type": "status",
                "run_id": run_id,
                "event": "completed",
                "status": "completed",
                "ended_at": _now_iso(),
            },
            required=True,
        )
    except Exception as exc:
        _queue_put(
            queue,
            {
                "type": "log",
                "run_id": run_id,
                "level": "ERROR",
                "message": f"Swarm failure: {exc}",
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": "System",
            },
        )
        _queue_put(
            queue,
            {
                "type": "log",
                "run_id": run_id,
                "level": "ERROR",
                "message": traceback.format_exc(),
                "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
                "role": "System",
            },
        )
        _queue_put(
            queue,
            {
                "type": "status",
                "run_id": run_id,
                "event": "failed",
                "status": "failed",
                "ended_at": _now_iso(),
                "failure_reason": str(exc),
            },
            required=True,
        )
    finally:
        _queue_put(queue, None, required=True)


def _wait_run_process(run_id: str, process: multiprocessing.Process, queue: Any) -> None:
    process.join()
    manifest = _load_json(_manifest_path(run_id))
    exit_code = process.exitcode
    status = manifest.get("status")
    if manifest and status not in FINAL_RUN_STATUSES:
        ended_at = _now_iso()
        if status == "stopping":
            next_status = "stopped"
            failure_reason = manifest.get("failure_reason")
        elif exit_code == 0:
            next_status = "completed"
            failure_reason = None
        elif exit_code is not None and exit_code < 0:
            next_status = "stopped"
            failure_reason = manifest.get("failure_reason")
        else:
            next_status = "failed"
            failure_reason = manifest.get("failure_reason") or f"worker exited with code {exit_code}"
        final_counts = _factor_summary_for_run(run_id)
        _write_run_manifest(
            run_id,
            {
                "status": next_status,
                "ended_at": ended_at,
                "failure_reason": failure_reason,
                "result_counts": final_counts,
            },
        )
        _append_jsonl(
            _log_path(run_id),
            {
                "type": "status",
                "run_id": run_id,
                "event": next_status,
                "status": next_status,
                "started_at": manifest.get("started_at"),
                "ended_at": ended_at,
                "failure_reason": failure_reason,
            },
        )
        _emit_event(
            {
                "type": "status",
                "run_id": run_id,
                "event": next_status,
                "status": next_status,
                "started_at": manifest.get("started_at"),
                "ended_at": ended_at,
                "failure_reason": failure_reason,
            }
        )
    try:
        _queue_put(queue, None, required=True)
    except Exception:
        pass
    _cleanup_run(run_id)


def _watch_swarm_run(run_id: str, process: multiprocessing.Process) -> None:
    started_monotonic = time.monotonic()
    interval = max(1, SWARM_RUN_HEARTBEAT_SECONDS)
    while True:
        time.sleep(interval)
        manifest = _load_json(_manifest_path(run_id))
        if not manifest or manifest.get("status") in FINAL_RUN_STATUSES:
            return
        try:
            if not process.is_alive():
                return
        except Exception:
            return

        elapsed = int(time.monotonic() - started_monotonic)
        if SWARM_RUN_TIMEOUT_SECONDS > 0 and elapsed >= SWARM_RUN_TIMEOUT_SECONDS:
            failure_reason = f"swarm exceeded timeout of {SWARM_RUN_TIMEOUT_SECONDS}s"
            _write_run_manifest(
                run_id,
                {
                    "status": "stopping",
                    "last_heartbeat_at": _now_iso(),
                    "elapsed_seconds": elapsed,
                    "failure_reason": failure_reason,
                },
            )
            event = {
                "type": "status",
                "run_id": run_id,
                "event": "timeout",
                "status": "stopping",
                "failure_reason": failure_reason,
                "started_at": manifest.get("started_at"),
            }
            _append_jsonl(_log_path(run_id), event)
            _emit_event(event)
            _stop_process_tree(process.pid)
            return

        _write_run_manifest(
            run_id,
            {
                "last_heartbeat_at": _now_iso(),
                "elapsed_seconds": elapsed,
                "timeout_seconds": SWARM_RUN_TIMEOUT_SECONDS,
            },
        )


def _paginate_rows(rows: list[sqlite3.Row], offset: int, limit: int) -> Dict[str, Any]:
    start = max(0, offset)
    page_limit = _list_limit(limit, LIST_PAGE_LIMIT_MAX)
    end = min(len(rows), start + page_limit)
    return {
        "items": [dict(row) for row in rows[start:end]],
        "total": len(rows),
        "offset": start,
        "limit": page_limit,
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
    chart_file = CHART_DIR / f"{factor_id}_curve.png"
    report_file = REPORT_DIR / f"{factor_id}.md"
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
    root = WIKI_DIR
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


_EVALUATION_MODE_ALIASES = {
    "rq": "ricequant",
    "rice_quant": "ricequant",
    "rice-quant": "ricequant",
}
_DATA_BACKEND_ALIASES = {
    **_EVALUATION_MODE_ALIASES,
    "csv": "local",
    "parquet": "local",
    "local_csv": "local",
    "local_parquet": "local",
}
_ENGINE_ALIASES = {"pd": "pandas", "pl": "polars"}
_MARKET_MODE_ALIASES = {
    "single_market": "single",
    "multi": "batch",
    "multiple": "batch",
    "hybrid": "mixed",
}
_MARKET_PROFILE_ALIASES = {
    "cn": "cn_stock",
    "china": "cn_stock",
    "a_share": "cn_stock",
    "a-share": "cn_stock",
    "us": "us_stock",
    "usa": "us_stock",
    "future": "futures",
}
_LOCAL_DATA_LAYOUT_ALIASES = {
    "single_file": "panel",
    "file": "panel",
    "qlib": "panel",
    "instrument": "instrument_files",
    "instrument_file": "instrument_files",
    "contract": "instrument_files",
    "contracts": "instrument_files",
    "dominant": "instrument_files",
}


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_choice(
    value: Any,
    *,
    field_name: str,
    allowed: tuple[str, ...],
    aliases: Optional[Dict[str, str]] = None,
    optional: bool = False,
) -> Optional[str]:
    text = _normalize_text(value)
    if text is None:
        if optional:
            return None
        raise ValueError(f"{field_name} is required")
    normalized = text.lower()
    normalized = (aliases or {}).get(normalized, normalized)
    if normalized not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed)}")
    return normalized


def _coerce_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            raw = json.loads(text)
            if isinstance(raw, list):
                return [str(item).strip() for item in raw if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in text.split(",") if item.strip()]


class RuntimeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, validate_default=True)

    @field_validator("mode", mode="before", check_fields=False)
    @classmethod
    def _validate_mode(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="mode",
                allowed=SUPPORTED_EVALUATION_MODES,
                aliases=_EVALUATION_MODE_ALIASES,
            )
        )

    @field_validator("data_backend", mode="before", check_fields=False)
    @classmethod
    def _validate_data_backend(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="data_backend",
                allowed=SUPPORTED_DATA_BACKENDS,
                aliases=_DATA_BACKEND_ALIASES,
            )
        )

    @field_validator("engine", mode="before", check_fields=False)
    @classmethod
    def _validate_engine(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="engine",
                allowed=ENGINE_CHOICES,
                aliases=_ENGINE_ALIASES,
            )
        )

    @field_validator("market_mode", mode="before", check_fields=False)
    @classmethod
    def _validate_market_mode(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="market_mode",
                allowed=SUPPORTED_MARKET_MODES,
                aliases=_MARKET_MODE_ALIASES,
            )
        )

    @field_validator("market_profile", mode="before", check_fields=False)
    @classmethod
    def _validate_market_profile(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="market_profile",
                allowed=SUPPORTED_MARKET_PROFILES,
                aliases=_MARKET_PROFILE_ALIASES,
            )
        )

    @field_validator("market_profiles", mode="before", check_fields=False)
    @classmethod
    def _validate_market_profiles(cls, value: Any) -> List[str]:
        profiles = [
            str(
                _normalize_choice(
                    item,
                    field_name="market_profiles",
                    allowed=SUPPORTED_MARKET_PROFILES,
                    aliases=_MARKET_PROFILE_ALIASES,
                )
            )
            for item in _coerce_string_list(value)
        ]
        return profiles

    @field_validator("local_data_layout", mode="before", check_fields=False)
    @classmethod
    def _validate_local_data_layout(cls, value: Any) -> str:
        return str(
            _normalize_choice(
                value,
                field_name="local_data_layout",
                allowed=SUPPORTED_LOCAL_DATA_LAYOUTS,
                aliases=_LOCAL_DATA_LAYOUT_ALIASES,
            )
        )

    @field_validator("llm_provider", mode="before", check_fields=False)
    @classmethod
    def _validate_llm_provider(cls, value: Any) -> Optional[str]:
        provider = _normalize_text(value)
        if provider is None:
            return None
        provider = provider.lower()
        if provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"llm_provider must be one of: {', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        return provider

    @field_validator("llm_reasoning_effort", mode="before", check_fields=False)
    @classmethod
    def _validate_llm_reasoning_effort(cls, value: Any) -> Optional[str]:
        effort = _normalize_text(value)
        if effort is None:
            return None
        effort = effort.lower()
        if effort not in SUPPORTED_LLM_REASONING_EFFORTS:
            raise ValueError(
                "llm_reasoning_effort must be one of: "
                f"{', '.join(SUPPORTED_LLM_REASONING_EFFORTS)}"
            )
        return effort

    @field_validator("embedding_provider", mode="before", check_fields=False)
    @classmethod
    def _validate_embedding_provider(cls, value: Any) -> Optional[str]:
        provider = _normalize_text(value)
        if provider is None:
            return None
        provider = provider.lower()
        if provider != "local" and provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(
                f"embedding_provider must be 'local' or one of: {', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        if provider == "codex":
            raise ValueError("embedding_provider='codex' is not supported")
        return provider

    @field_validator("llm_base_url", "local_data_path", mode="before", check_fields=False)
    @classmethod
    def _blank_to_none(cls, value: Any) -> Optional[str]:
        return _normalize_text(value)

    @model_validator(mode="after")
    def _validate_runtime_consistency(self) -> "RuntimeRequestModel":
        market_profile = getattr(self, "market_profile", None)
        market_profiles = list(getattr(self, "market_profiles", None) or [])
        if market_profile:
            if getattr(self, "market_mode", None) == "single":
                setattr(self, "market_profiles", [market_profile])
            elif market_profile not in market_profiles:
                setattr(self, "market_profiles", [market_profile] + market_profiles)
        if getattr(self, "data_backend", None) == "local" and not getattr(self, "local_data_path", None):
            raise ValueError("local_data_path is required when data_backend='local'")
        return self


class SwarmConfig(RuntimeRequestModel):
    iterations: int = Field(default=2, ge=1)
    mode: str = Field(
        default="ricequant",
        validation_alias=AliasChoices("mode", "evaluation_mode"),
    )
    data_backend: str = "ricequant"
    engine: str = Field(
        default="polars",
        validation_alias=AliasChoices("engine", "evaluation_engine"),
    )
    roles: List[str]
    market_start: str = "2017-01-01"
    market_end: str = "2020-10-31"
    llm_provider: str = "kimi"
    llm_model: str = "kimi-k2-turbo-preview"
    llm_base_url: Optional[str] = None
    llm_reasoning_effort: Optional[str] = None
    embedding_provider: Optional[str] = None
    market_mode: str = "single"
    market_profile: str = "cn_stock"
    market_profiles: List[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"
    parallel: bool = True
    client_run_key: Optional[str] = Field(
        default=None,
        description="Optional idempotency key. Reusing it returns the existing run instead of creating a duplicate.",
    )

    @field_validator("roles", mode="before")
    @classmethod
    def _validate_roles(cls, value: Any) -> List[str]:
        roles = _coerce_string_list(value)
        if not roles:
            raise ValueError("roles must contain at least one role")
        return roles

    @field_validator("client_run_key")
    @classmethod
    def _validate_client_run_key(cls, value: Optional[str]) -> Optional[str]:
        value = _normalize_text(value)
        if value is None:
            return None
        if len(value) > 80 or not SAFE_ID_RE.match(value):
            raise ValueError("client_run_key must be 1-80 chars of letters, numbers, '_' or '-'")
        return value


class BacktestRequest(RuntimeRequestModel):
    expression: str = Field(
        ...,
        description="Raw Qlib-style factor expression, e.g. 'Rank(Delta($close, 5))'.",
    )
    start_date: str = "2017-01-01"
    end_date: str = "2020-10-31"
    engine: str = Field(
        default="polars",
        description="'pandas' or 'polars'",
        validation_alias=AliasChoices("engine", "evaluation_engine"),
    )
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


class StrategyRunRequest(RuntimeRequestModel):
    expression: str
    strategy_config: Dict[str, Any]
    data_backend: str = "ricequant"
    market_profile: str = "cn_stock"
    market_mode: str = "single"
    market_profiles: List[str] = Field(default_factory=lambda: ["cn_stock"])
    local_data_path: Optional[str] = None
    local_data_layout: str = "auto"


def _shutdown_active_swarm_runs() -> None:
    with state.lock:
        active_states = dict(state.runs)

    run_ids = set(active_states)
    if SWARM_RUN_DIR.exists():
        run_ids.update(path.stem for path in SWARM_RUN_DIR.glob("run_*.json"))

    for run_id in sorted(run_ids):
        manifest = _load_json(_manifest_path(run_id))
        run_state = active_states.get(run_id)
        active_pid = _resolve_active_pid(manifest, run_state)
        if active_pid is None:
            continue

        started_at = manifest.get("started_at")
        _write_run_manifest(
            run_id,
            {
                "status": "stopping",
                "ended_at": None,
                "failure_reason": manifest.get("failure_reason"),
            },
        )
        stopping_event = {
            "type": "status",
            "run_id": run_id,
            "event": "stopping",
            "status": "stopping",
            "started_at": started_at,
            "reason": "api_shutdown",
        }
        _append_jsonl(_log_path(run_id), stopping_event)

        _stop_process_tree(active_pid)
        if run_state and run_state.process:
            try:
                run_state.process.join(timeout=5)
            except TypeError:
                run_state.process.join()
            except Exception:
                pass
        if run_state and run_state.queue:
            _queue_put(run_state.queue, None, required=True)

        ended_at = _now_iso()
        _write_run_manifest(
            run_id,
            {
                "status": "stopped",
                "ended_at": ended_at,
                "failure_reason": manifest.get("failure_reason"),
            },
        )
        _append_jsonl(
            _log_path(run_id),
            {
                "type": "status",
                "run_id": run_id,
                "event": "stopped",
                "status": "stopped",
                "started_at": started_at,
                "ended_at": ended_at,
                "reason": "api_shutdown",
            },
        )
        _cleanup_run(run_id)


@app.on_event("startup")
async def startup_event() -> None:
    _ensure_runtime_dirs()
    if DB_PATH.exists():
        with _db_connect() as conn:
            _ensure_db_schema(conn)
    state.loop = asyncio.get_running_loop()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    _shutdown_active_swarm_runs()
    with state.lock:
        state.sockets.clear()
        state.loop = None


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
        "readiness": _readiness_payload(),
    }


@app.get("/api/readiness")
def readiness() -> Dict[str, Any]:
    return _readiness_payload()


@app.get("/api/results")
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
            select_cols = _select_projection(existing, _ALPHA_POOL_RESULT_COLUMNS)
            order_clause = "timestamp DESC" if "timestamp" in existing else "rowid DESC"
            if run_id:
                if "run_id" not in existing:
                    rows = []
                else:
                    rows = conn.execute(
                        f"SELECT {select_cols} FROM alpha_pool WHERE run_id=? ORDER BY {order_clause}",
                        (run_id,),
                    ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM alpha_pool ORDER BY {order_clause}"
                ).fetchall()
    return _paginate_rows(list(rows), offset, limit)


@app.get("/api/factors/{factor_id}")
def get_factor_detail(factor_id: str) -> Dict[str, Any]:
    factor_id = _safe_segment(factor_id)
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        row = conn.execute("SELECT * FROM alpha_pool WHERE id=?", (factor_id,)).fetchone()
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


@app.get("/api/charts/{factor_id}")
def get_chart(factor_id: str) -> FileResponse:
    factor_id = _safe_segment(factor_id)
    path = CHART_DIR / f"{factor_id}_curve.png"
    if not path.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(str(path), media_type="image/png")


@app.get("/api/reports/{factor_id}", response_class=PlainTextResponse)
def get_report(factor_id: str) -> PlainTextResponse:
    factor_id = _safe_segment(factor_id)
    path = REPORT_DIR / f"{factor_id}.md"
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
        "limit": page_limit,
        "next_offset": end,
    }


@app.get("/api/wiki/page/{slug}", response_class=PlainTextResponse)
def wiki_page(slug: str) -> PlainTextResponse:
    slug = _safe_segment(slug)
    path = WIKI_DIR / f"{slug}.md"
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


class WikiPageUpdateRequest(BaseModel):
    content: str = Field(min_length=1, description="Full markdown page content including optional frontmatter.")


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


@app.put("/api/wiki/page/{slug}")
def wiki_update_page(
    slug: str,
    req: WikiPageUpdateRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    slug = _safe_segment(slug)
    path = WIKI_DIR / f"{slug}.md"
    if path.name in {"index.md", "log.md"}:
        raise HTTPException(400, "system wiki pages are read-only")
    if not path.exists():
        raise HTTPException(404, "wiki page not found")
    meta, _body = parse_wiki_frontmatter(req.content)
    frontmatter_slug = str(meta.get("slug") or "").strip()
    if frontmatter_slug and _safe_segment(frontmatter_slug) != slug:
        raise HTTPException(400, "frontmatter slug must match requested slug")
    _audit(actor, "wiki.update", slug)
    normalized = req.content.rstrip() + "\n"
    path.write_text(normalized, encoding="utf-8")
    return {"status": "saved", "slug": slug, "bytes": len(normalized.encode("utf-8"))}


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
            detail=f"backtest exceeded timeout of {MANUAL_BACKTEST_TIMEOUT_SECONDS}s",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(f"[Manual BT] Unhandled error: {exc}\n{traceback.format_exc()}")
        raise _service_error(exc, "backtest failed")
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
            detail=f"strategy backtest exceeded timeout of {STRATEGY_BACKTEST_TIMEOUT_SECONDS}s",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        logger.error(f"[Strategy BT] Unhandled error: {exc}\n{traceback.format_exc()}")
        raise _service_error(exc, "strategy backtest failed")
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
        return _empty_page(offset, limit)
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        existing = _table_columns(conn, "strategy_backtests")
        if not existing:
            rows = []
        else:
            select_cols = _select_projection(existing, _STRATEGY_LIST_COLUMNS)
            order_clause = "ran_at DESC" if "ran_at" in existing else "rowid DESC"
            if run_id:
                if "run_id" not in existing:
                    rows = []
                else:
                    rows = conn.execute(
                        f"SELECT {select_cols} FROM strategy_backtests WHERE run_id=? ORDER BY {order_clause}",
                        (run_id,),
                    ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {select_cols} FROM strategy_backtests ORDER BY {order_clause}"
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


@app.delete("/api/strategy/{strategy_id}")
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


@app.get("/api/strategies/{strategy_id}/charts/{kind}")
def get_strategy_chart(strategy_id: str, kind: str) -> FileResponse:
    strategy_id = _safe_segment(strategy_id)
    if kind not in {"equity", "turnover"}:
        raise HTTPException(400, "invalid chart kind")
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_strategy_backtests_schema(conn)
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
        existing_run_id = _find_run_by_client_key(config.client_run_key)
        if existing_run_id:
            return {"status": "existing", "run_id": existing_run_id}
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
                "last_heartbeat_at": _now_iso(),
                "elapsed_seconds": 0,
                "timeout_seconds": SWARM_RUN_TIMEOUT_SECONDS,
                "parallel": bool(config.parallel),
                "config": config_payload,
                "result_counts": {"factor_count": 0, "strategy_count": 0},
            },
        )
        queue = multiprocessing.Queue(maxsize=SWARM_QUEUE_MAXSIZE)
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
        process_create_time = None
        try:
            process_create_time = psutil.Process(process.pid).create_time()
        except psutil.Error:
            pass
        _write_run_manifest(
            run_id,
            {
                "process_pid": process.pid,
                "process_create_time": process_create_time,
                "status": "running",
            },
        )
        _register_run(run_id, process, queue, listener_thread, config_payload)
    threading.Thread(
        target=_wait_run_process,
        args=(run_id, process, queue),
        daemon=True,
    ).start()
    threading.Thread(
        target=_watch_swarm_run,
        args=(run_id, process),
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
    return _annotate_run_manifest(run_id, manifest, run_state, persist=True)


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
    if current_status == "stopping":
        return {"status": current_status, "run_id": run_id}
    if current_status in {"completed", "failed", "stopped"}:
        return {"status": current_status, "run_id": run_id}
    active_pid = _resolve_active_pid(manifest, run_state)
    if active_pid is None:
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
        _cleanup_run(run_id)
        return {"status": "stopped", "run_id": run_id}
    _write_run_manifest(
        run_id,
        {
            "status": "stopping",
            "ended_at": None,
        },
    )
    if run_state:
        run_state.status = "stopping"
    event = {
        "type": "status",
        "run_id": run_id,
        "event": "stopping",
        "status": "stopping",
        "started_at": manifest.get("started_at"),
    }
    _append_jsonl(_log_path(run_id), event)
    _emit_event(event)
    _stop_process_tree(active_pid)
    return {"status": "stopping", "run_id": run_id}


@app.delete("/api/swarm/runs/{run_id}")
def delete_swarm_run(
    run_id: str,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    run_id = _safe_segment(run_id)
    _audit(actor, "swarm.delete", run_id)
    manifest = _load_run_manifest(run_id)
    with state.lock:
        run_state = state.runs.get(run_id)
    if _resolve_active_pid(manifest, run_state) is not None:
        raise HTTPException(409, "run is still active; stop it first")
    manifest_path = _manifest_path(run_id)
    lock_path = _manifest_lock_path(run_id)
    log_path = _log_path(run_id)
    if not manifest_path.exists() and not log_path.exists():
        raise HTTPException(404, "run not found")
    for path in (manifest_path, log_path, lock_path):
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
    return {"status": "deleted", "run_id": run_id}


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
    with state.lock:
        state.sockets.add(websocket)
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
        with state.lock:
            state.sockets.discard(websocket)


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
    import multiprocessing
    multiprocessing.freeze_support()

    uvicorn.run(app, host="0.0.0.0", port=8000)
