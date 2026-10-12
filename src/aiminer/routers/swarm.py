"""Swarm run lifecycle, orchestration, and worker management APIRouter."""

from __future__ import annotations

import json
import multiprocessing
import os
import queue as queue_module
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from aiminer.core.runtime import new_run_id
from aiminer.routers.common import *

router = APIRouter(tags=["swarm"])
swarm_router = router


@swarm_router.get("/api/swarm/status")
def swarm_status(actor: Actor = Depends(_require_actor)) -> Dict[str, Any]:
    _audit(actor, "swarm.status", "global")
    return {
        "running_count": state.running_count(),
        "active_run_ids": state.active_run_ids(),
        "max_concurrent": MAX_CONCURRENT_SWARMS,
    }


@swarm_router.get("/api/swarm/runs")
def list_swarm_runs(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    _audit(actor, "swarm.list", "global", {"status": status_filter})
    return _list_run_manifests(
        offset=offset, limit=limit, status_filter=status_filter
    )


@swarm_router.post("/api/swarm/runs")
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


@swarm_router.get("/api/swarm/runs/{run_id}")
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


@swarm_router.get("/api/swarm/runs/{run_id}/logs")
def get_swarm_run_logs(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LOG_PAGE_LIMIT_DEFAULT, ge=1),
    tail: bool = Query(default=False),
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    run_id = _safe_segment(run_id)
    _audit(
        actor,
        "swarm.logs",
        run_id,
        {"offset": offset, "limit": limit, "tail": tail},
    )
    if not _manifest_path(run_id).exists():
        raise HTTPException(404, "run not found")
    return _load_jsonl_slice(
        _log_path(run_id), offset=offset, limit=limit, tail=tail
    )


@swarm_router.post("/api/swarm/runs/{run_id}/stop")
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


@swarm_router.delete("/api/swarm/runs/{run_id}")
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
