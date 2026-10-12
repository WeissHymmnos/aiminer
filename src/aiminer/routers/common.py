# --- Imports & Configuration ---
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import queue as queue_module
import re
import sqlite3
import threading
import time
import traceback
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from loguru import logger
import psutil
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from aiminer.core import manual_runner  # noqa: F401  (import-for-side-effect)
from aiminer.core.runtime import new_run_id
from aiminer.core.settings import (
    SUPPORTED_DATA_BACKENDS,
    SUPPORTED_EVALUATION_MODES,
    SUPPORTED_LLM_PROVIDERS,
    SUPPORTED_LLM_REASONING_EFFORTS,
    SUPPORTED_LOCAL_DATA_LAYOUTS,
    SUPPORTED_MARKET_MODES,
    SUPPORTED_MARKET_PROFILES,
    build_settings,
)
from aiminer.core.wiki import _parse_frontmatter as parse_wiki_frontmatter
from aiminer.manager import PortfolioManager

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
SWARM_RUN_TIMEOUT_SECONDS = int(
    os.getenv("AIMINER_SWARM_RUN_TIMEOUT_SECONDS", "3600")
)
SWARM_RUN_HEARTBEAT_SECONDS = int(
    os.getenv("AIMINER_SWARM_RUN_HEARTBEAT_SECONDS", "15")
)
MANUAL_BACKTEST_TIMEOUT_SECONDS = int(
    os.getenv("AIMINER_MANUAL_BACKTEST_TIMEOUT_SECONDS", "600")
)
STRATEGY_BACKTEST_TIMEOUT_SECONDS = int(
    os.getenv("AIMINER_STRATEGY_BACKTEST_TIMEOUT_SECONDS", "900")
)
CROSSOVER_TIMEOUT_SECONDS = int(
    os.getenv("AIMINER_CROSSOVER_TIMEOUT_SECONDS", "1200")
)
LOG_PAGE_LIMIT_DEFAULT = 100
LOG_PAGE_LIMIT_MAX = 500
LIST_PAGE_LIMIT_DEFAULT = 50
LIST_PAGE_LIMIT_MAX = 200
AUTH_TOKEN = os.getenv("AIMINER_AUTH_TOKEN")
AUTH_DISABLED = (
    os.getenv("AIMINER_DISABLE_AUTH", "").lower() in {"1", "true", "yes"}
    or not AUTH_TOKEN
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "AIMINER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
HTTP_BEARER = HTTPBearer(auto_error=False)
ACTIVE_RUN_STATUSES = {"starting", "pending", "running"}
FINAL_RUN_STATUSES = {"completed", "failed", "stopped"}
ENGINE_CHOICES = ("pandas", "polars")
_MANIFEST_LOCKS: Dict[str, threading.RLock] = {}
_MANIFEST_LOCKS_GUARD = threading.Lock()


# --- Runtime Helpers ---
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
    "dsr": "REAL",
    "n_trials": "INTEGER",
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
    is_simulated INTEGER,
    dsr REAL,
    n_trials INTEGER
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


# --- Database Schema & Access ---
def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {
            str(row[1])
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_alpha_timestamp ON "
            "alpha_pool(timestamp)"
    )
    if "run_id" in _table_columns(conn, "alpha_pool"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alpha_run_id ON alpha_pool(run_id)"
        )


def _ensure_strategy_backtests_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_STRATEGY_BACKTESTS_TABLE_SQL)
    _ensure_optional_columns(
        conn, "strategy_backtests", _STRATEGY_BACKTEST_OPTIONAL_COLUMNS
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_ran_at ON "
            "strategy_backtests(ran_at)"
    )
    if "run_id" in _table_columns(conn, "strategy_backtests"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_backtests_run_id ON "
            "strategy_backtests(run_id)"
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


def _empty_page(
    offset: int, limit: int, maximum: int = LIST_PAGE_LIMIT_MAX
) -> Dict[str, Any]:
    start = max(0, offset)
    page_limit = _list_limit(limit, maximum)
    return {
        "items": [],
        "total": 0,
        "offset": start,
        "limit": page_limit,
        "next_offset": start,
    }


# --- Run Manifest & Process Control ---
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
        logger.warning(
            f"[counts] failed to count {table}.{column} for {value}: {exc}"
        )
        return 0


def _factor_summary_for_run(run_id: str) -> Dict[str, int]:
    return {
        "factor_count": _count_rows("alpha_pool", "run_id", run_id),
        "strategy_count": _count_rows("strategy_backtests", "run_id", run_id),
    }


def _readiness_payload() -> Dict[str, Any]:
    from aiminer.core.rag import (
        chroma_sqlite_summary,
        resolve_embedding_model_tag,
    )

    model_tag = resolve_embedding_model_tag(SETTINGS.embedding_provider)
    rag = chroma_sqlite_summary(
        str(SETTINGS.data_path / "chroma_db"), model_tag
    )
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


def _resolve_active_pid(
    manifest: Dict[str, Any], run_state: Optional["RunState"] = None
) -> Optional[int]:
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
    started = _parse_iso_datetime(
        manifest.get("started_at") or manifest.get("created_at")
    )
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
    if (
        status in ACTIVE_RUN_STATUSES
        and manifest.get("process_pid")
        and not is_active
    ):
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
        if normalized_status in FINAL_RUN_STATUSES and not manifest.get(
            "ended_at"
        ):
            patch["ended_at"] = _now_iso()
        elif normalized_status not in FINAL_RUN_STATUSES and manifest.get(
            "ended_at"
        ):
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
            if (
                _resolve_active_pid(manifest, active_states.get(run_id))
                is not None
            ):
                run_ids.add(run_id)
    return sorted(run_ids)


# --- WebSocket & Global State ---
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


# --- Auth & Audit ---
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


def _audit(
    actor: Actor,
    action: str,
    target: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
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
            detail=(
            "RiceQuant disconnected from the remote server. Retry later, "
            "or switch Data Backend to local/qlib."
        ),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message
    )


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


def _list_run_manifests(
    offset: int = 0,
    limit: int = LIST_PAGE_LIMIT_DEFAULT,
    status_filter: Optional[str] = None,
) -> Dict[str, Any]:
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
            manifest = _annotate_run_manifest(
                run_id, manifest, active_states.get(run_id), persist=True
            )
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
        if (
            isinstance(config, dict)
            and config.get("client_run_key") == client_run_key
        ):
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
        if (
            not required
            and isinstance(payload, dict)
            and payload.get("type") == "log"
        ):
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
                        "strategy_count": int(
                            record.get("strategy_count") or 0
                        ),
                    }
                },
            )
        _emit_event(record)


def _swarm_process_target(
    run_id: str, config: Dict[str, Any], queue: Any
) -> None:
    def queue_log(
        level: str, message: str, role: str, agent_id: Optional[str] = None
    ) -> None:
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
        manager.run_swarm(
            parallel=bool(config.get("parallel")), log_queue=queue
        )
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


def _wait_run_process(
    run_id: str, process: multiprocessing.Process, queue: Any
) -> None:
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
            failure_reason = (
                manifest.get("failure_reason")
                or f"worker exited with code {exit_code}"
            )
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
        if (
            SWARM_RUN_TIMEOUT_SECONDS > 0
            and elapsed >= SWARM_RUN_TIMEOUT_SECONDS
        ):
            failure_reason = (
                f"swarm exceeded timeout of {SWARM_RUN_TIMEOUT_SECONDS}s"
            )
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


def _paginate_rows(
    rows: list[sqlite3.Row], offset: int, limit: int
) -> Dict[str, Any]:
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
    for column in (
        "metrics_json",
        "returns_json",
        "best_strategy_metrics_json",
    ):
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
    payload["chart_url"] = (
        f"/api/charts/{factor_id}" if chart_file.exists() else None
    )
    payload["report_url"] = (
        f"/api/reports/{factor_id}" if report_file.exists() else None
    )
    return payload


def _factor_perf_for_selection(factor: Dict[str, Any]) -> float:
    for key in ("perf_metric", "ic"):
        value = _safe_float(factor.get(key))
        if value is not None:
            return value
    metrics = factor.get("metrics") or {}
    value = _safe_float(metrics.get("information_coefficient"))
    return value if value is not None else 0.0


def _load_crossover_factor_pool(
    factor_ids: List[str],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not DB_PATH.exists():
        raise HTTPException(404, "db missing")
    with _db_connect() as conn:
        _ensure_db_schema(conn)
        rows = conn.execute(
            "SELECT * FROM alpha_pool ORDER BY timestamp DESC"
        ).fetchall()
    factors = [_row_to_factor_detail(row) for row in rows]
    if not factors:
        raise HTTPException(400, "alpha pool is empty")

    if factor_ids:
        by_id = {str(factor.get("id")): factor for factor in factors}
        missing = [
            factor_id for factor_id in factor_ids if factor_id not in by_id
        ]
        if missing:
            raise HTTPException(404, f"factor not found: {', '.join(missing)}")
        parents = [by_id[factor_id] for factor_id in factor_ids]
    else:
        eligible = [
            factor
            for factor in factors
            if factor.get("code") and not bool(factor.get("is_simulated"))
        ]
        parents = sorted(
            eligible, key=_factor_perf_for_selection, reverse=True
        )[:2]

    if len(parents) < 2:
        raise HTTPException(
            400, "at least two factors are required for crossover"
        )
    missing_code = [
        str(factor.get("id")) for factor in parents if not factor.get("code")
    ]
    if missing_code:
        raise HTTPException(
            400, f"parent factor has no code: {', '.join(missing_code)}"
        )
    return parents, factors


def _crossover_manager_kwargs(
    req: "FactorCrossoverRequest", parents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    base = parents[0] if parents else {}
    data_backend = (
        req.data_backend or base.get("data_backend") or SETTINGS.data_backend
    )
    evaluation_mode = (
        req.mode
        or base.get("evaluation_mode")
        or ("qlib" if data_backend == "qlib" else "ricequant")
    )
    market_profile = (
        req.market_profile
        or base.get("market_profile")
        or SETTINGS.market_profile
    )
    market_mode = (
        req.market_mode or base.get("market_mode") or SETTINGS.market_mode
    )
    market_profiles = req.market_profiles or [market_profile]

    return {
        "run_id": req.run_id or new_run_id(),
        "max_iterations": 1,
        "evaluation_mode": evaluation_mode,
        "data_backend": data_backend,
        "evaluation_engine": req.engine
        or base.get("evaluation_engine")
        or SETTINGS.evaluation_engine,
        "llm_provider": req.llm_provider or SETTINGS.llm_provider,
        "llm_model": req.llm_model or SETTINGS.llm_model,
        "llm_base_url": req.llm_base_url or SETTINGS.llm_base_url,
        "llm_reasoning_effort": req.llm_reasoning_effort
        or SETTINGS.llm_reasoning_effort,
        "embedding_provider": req.embedding_provider
        or SETTINGS.embedding_provider,
        "market_mode": market_mode,
        "market_profile": market_profile,
        "market_profiles": market_profiles,
        "local_data_path": req.local_data_path or SETTINGS.local_data_path,
        "local_data_layout": req.local_data_layout
        or SETTINGS.local_data_layout,
        "market_start": req.market_start or SETTINGS.market_start,
        "market_end": req.market_end or SETTINGS.market_end,
        "crossover_iterations": req.crossover_iterations,
    }


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
    payload["expression"] = payload.get("expression_payload", {}).get(
        "expression"
    )
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
                edges.append(
                    {"source": slug, "target": target, "kind": "related"}
                )
                degree_map[slug] += 1
                degree_map[target] += 1
        for target in page["wikilinks"]:
            if target not in pages:
                continue
            key = (slug, target, "wikilink")
            if key not in edges_seen:
                edges_seen.add(key)
                edges.append(
                    {"source": slug, "target": target, "kind": "wikilink"}
                )
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
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, validate_default=True
    )

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
                "llm_provider must be one of: "
                f"{', '.join(SUPPORTED_LLM_PROVIDERS)}"
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
                "embedding_provider must be 'local' or one of: "
                f"{', '.join(SUPPORTED_LLM_PROVIDERS)}"
            )
        if provider == "codex":
            raise ValueError("embedding_provider='codex' is not supported")
        return provider

    @field_validator(
        "llm_base_url", "local_data_path", mode="before", check_fields=False
    )
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
                setattr(
                    self, "market_profiles", [market_profile] + market_profiles
                )
        if getattr(self, "data_backend", None) == "local" and not getattr(
            self, "local_data_path", None
        ):
            raise ValueError(
                "local_data_path is required when data_backend='local'"
            )
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
        description=(
            "Optional idempotency key. Reusing it returns the existing "
            "run instead of creating a duplicate."
        ),
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
            raise ValueError(
                "client_run_key must be 1-80 chars of letters, numbers, "
                "'_' or '-'"
            )
        return value


class BacktestRequest(RuntimeRequestModel):
    expression: str = Field(
        ...,
        description=(
            "Raw Qlib-style factor expression, e.g. "
            "'Rank(Delta($close, 5))'."
        ),
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


class FactorCrossoverRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, validate_default=True
    )

    factor_ids: List[str] = Field(
        default_factory=list,
        description=(
            "Optional parent factor ids. Empty means use the top two "
            "factors in Alpha Pool."
        ),
    )
    crossover_iterations: int = Field(default=1, ge=1, le=20)
    acceptance_threshold: float = Field(default=0.01, ge=0)
    run_id: Optional[str] = None
    mode: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("mode", "evaluation_mode"),
    )
    data_backend: Optional[str] = None
    engine: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("engine", "evaluation_engine"),
    )
    market_start: Optional[str] = None
    market_end: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_reasoning_effort: Optional[str] = None
    embedding_provider: Optional[str] = None
    market_mode: Optional[str] = None
    market_profile: Optional[str] = None
    market_profiles: List[str] = Field(default_factory=list)
    local_data_path: Optional[str] = None
    local_data_layout: Optional[str] = None

    @field_validator("factor_ids", mode="before")
    @classmethod
    def _validate_factor_ids(cls, value: Any) -> List[str]:
        ids = []
        seen = set()
        for factor_id in _coerce_string_list(value):
            if len(factor_id) > 80 or not SAFE_ID_RE.match(factor_id):
                raise ValueError(
                    "factor_ids must contain valid factor identifiers"
                )
            if factor_id not in seen:
                ids.append(factor_id)
                seen.add(factor_id)
        if len(ids) == 1:
            raise ValueError(
                "factor_ids must contain zero ids or at least two ids"
            )
        return ids

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: Optional[str]) -> Optional[str]:
        value = _normalize_text(value)
        if value is None:
            return None
        if len(value) > 80 or not SAFE_ID_RE.match(value):
            raise ValueError(
                "run_id must be 1-80 chars of letters, numbers, '_' or '-'"
            )
        return value

    @field_validator("mode", mode="before")
    @classmethod
    def _validate_optional_mode(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="mode",
            allowed=SUPPORTED_EVALUATION_MODES,
            aliases=_EVALUATION_MODE_ALIASES,
            optional=True,
        )

    @field_validator("data_backend", mode="before")
    @classmethod
    def _validate_optional_data_backend(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="data_backend",
            allowed=SUPPORTED_DATA_BACKENDS,
            aliases=_DATA_BACKEND_ALIASES,
            optional=True,
        )

    @field_validator("engine", mode="before")
    @classmethod
    def _validate_optional_engine(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="engine",
            allowed=ENGINE_CHOICES,
            aliases=_ENGINE_ALIASES,
            optional=True,
        )

    @field_validator("market_mode", mode="before")
    @classmethod
    def _validate_optional_market_mode(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="market_mode",
            allowed=SUPPORTED_MARKET_MODES,
            aliases=_MARKET_MODE_ALIASES,
            optional=True,
        )

    @field_validator("market_profile", mode="before")
    @classmethod
    def _validate_optional_market_profile(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="market_profile",
            allowed=SUPPORTED_MARKET_PROFILES,
            aliases=_MARKET_PROFILE_ALIASES,
            optional=True,
        )

    @field_validator("market_profiles", mode="before")
    @classmethod
    def _validate_optional_market_profiles(cls, value: Any) -> List[str]:
        return [
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

    @field_validator("local_data_layout", mode="before")
    @classmethod
    def _validate_optional_local_data_layout(cls, value: Any) -> Optional[str]:
        return _normalize_choice(
            value,
            field_name="local_data_layout",
            allowed=SUPPORTED_LOCAL_DATA_LAYOUTS,
            aliases=_LOCAL_DATA_LAYOUT_ALIASES,
            optional=True,
        )

    @field_validator(
        "llm_provider",
        "llm_model",
        "llm_base_url",
        "llm_reasoning_effort",
        "embedding_provider",
        "market_start",
        "market_end",
        "local_data_path",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: Any) -> Optional[str]:
        return _normalize_text(value)


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


class ResetRequest(BaseModel):
    scopes: List[str] = Field(
        default_factory=lambda: ["pool"],
        description="One or more of: pool, memory, rag, runs, all.",
    )
    confirm: bool = Field(
        default=False,
        description=(
            "When false, returns the dry-run plan without moving anything."
        ),
    )
    reset_token: Optional[str] = Field(
        default=None,
        description=(
            "Required when confirm=true: must equal AIMINER_RESET_TOKEN env "
            "var. Defends against accidental destructive POSTs by "
            "reusing-API-token clients."
        ),
    )


class WikiPageUpdateRequest(BaseModel):
    content: str = Field(
        min_length=1,
        description=(
            "Full markdown page content including optional frontmatter."
        ),
    )


FRONTEND_DIST_DIR = _resolve_frontend_dist_dir()

__all__ = [k for k in list(globals().keys()) if not k.startswith("__")]
