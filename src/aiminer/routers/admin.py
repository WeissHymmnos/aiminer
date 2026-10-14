"""Admin, health check, and system readiness APIRouter."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from aiminer.routers.common import *

router = APIRouter(tags=["admin"])
admin_router = router


@admin_router.get("/", response_model=None)
def read_index():
    index_path = _frontend_index_path()
    if index_path:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return PlainTextResponse(
        "AIMiner API server.\nFrontend assets are not built.\n",
        media_type="text/plain; charset=utf-8",
    )


@admin_router.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "auth_disabled": AUTH_DISABLED,
        "active_run_ids": state.active_run_ids(),
        "readiness": _readiness_payload(),
    }


@admin_router.get("/api/readiness")
def readiness() -> Dict[str, Any]:
    return _readiness_payload()


@admin_router.post("/api/admin/reset")
def admin_reset(
    req: ResetRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    """Wipe mining artifacts.

    Always reversible (moves into results/.trash/<ts>/).
    """
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

    _audit(
        actor, "admin.reset", ",".join(plan.scopes), {"confirm": req.confirm}
    )
    summary = execute_plan(plan, confirm=req.confirm)
    summary["plan_text"] = render_plan(plan)
    return summary


def _finaince_platform_db() -> Path:
    home = os.getenv("FINAINCE_HOME", "").strip()
    base = Path(home).expanduser() if home else Path("~/.finaince").expanduser()
    return base / "platform.db"


@admin_router.get("/api/v1/health")
def v1_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "product": "FinAlpha",
        "degraded": False,
    }


@admin_router.get("/api/v1/catalog")
def v1_catalog(
    source: Optional[str] = None,
    query: str = "",
    style: Optional[str] = None,
) -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    items: List[Dict[str, Any]] = []
    q_lower = query.strip().lower()
    if db_path.is_file():
        try:
            with sqlite3.connect(str(db_path), timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT record_json FROM factor_catalog ORDER BY updated_at DESC"
                ).fetchall()
                for row in rows:
                    try:
                        rec = json.loads(row["record_json"])
                    except Exception:
                        continue
                    if source and (rec.get("lineage") or {}).get("source") != source:
                        continue
                    if style and rec.get("style") != style:
                        continue
                    if q_lower:
                        hay = " ".join(
                            str(x or "")
                            for x in (
                                rec.get("id"),
                                rec.get("name"),
                                rec.get("name_cn"),
                                (rec.get("expression") or {}).get("text"),
                            )
                        ).lower()
                        if q_lower not in hay:
                            continue
                    items.append(rec)
        except Exception:
            pass
    return {"items": items, "count": len(items)}


@admin_router.get("/api/v1/catalog/{catalog_id}")
def v1_catalog_detail(catalog_id: str) -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    if db_path.is_file():
        try:
            with sqlite3.connect(str(db_path), timeout=10.0) as conn:
                row = conn.execute(
                    "SELECT record_json FROM factor_catalog WHERE id = ?",
                    (catalog_id,),
                ).fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            pass
    raise HTTPException(status_code=404, detail="unknown catalog id")


@admin_router.post("/api/v1/promote")
def v1_promote(body: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import timezone
    import uuid

    cid = str(body.get("catalog_id") or "").strip()
    if not cid:
        raise HTTPException(status_code=400, detail="catalog_id required")
    direction = str(body.get("direction") or "to_pool").strip()
    if direction not in ("to_pool", "to_library"):
        raise HTTPException(
            status_code=400, detail="direction must be to_pool|to_library"
        )
    rec = v1_catalog_detail(cid)
    failures: List[str] = []
    details: Dict[str, Any] = {}
    if rec.get("universe") == "local_panel":
        failures.append("thin_panel")
        details["thin_panel"] = "local_panel is a smoke panel"
    ic_val = (rec.get("metrics") or {}).get("ic")
    if ic_val is None or abs(float(ic_val)) < 0.02:
        failures.append("weak_ic")
        details["weak_ic"] = f"ic={ic_val}"
    gates = {
        "passed": len(failures) == 0,
        "failures": failures,
        "direction": direction,
        "details": details,
    }
    promo_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    db_path = _finaince_platform_db()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path), timeout=10.0) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promotion_events (
                id TEXT PRIMARY KEY,
                catalog_id TEXT,
                direction TEXT,
                decision TEXT,
                gate_json TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO promotion_events (id, catalog_id, direction, decision, gate_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (promo_id, cid, direction, "pending", json.dumps(gates), now),
        )
        conn.commit()
    return {
        "ok": True,
        "promotion_id": promo_id,
        "catalog_id": cid,
        "direction": direction,
        "decision": "pending",
        "gates": gates,
    }


@admin_router.get("/api/v1/review")
def v1_review_queue() -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    items: List[Dict[str, Any]] = []
    if db_path.is_file():
        try:
            with sqlite3.connect(str(db_path), timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, catalog_id, direction, decision, gate_json, created_at FROM promotion_events WHERE decision = 'pending' ORDER BY created_at DESC"
                ).fetchall()
                for row in rows:
                    try:
                        gates = json.loads(row["gate_json"] or "{}")
                    except Exception:
                        gates = {}
                    items.append(
                        {
                            "id": row["id"],
                            "catalog_id": row["catalog_id"],
                            "direction": row["direction"],
                            "decision": row["decision"],
                            "gates": gates,
                            "created_at": row["created_at"],
                        }
                    )
        except Exception:
            pass
    return {"items": items}


@admin_router.get("/api/v1/review/{promotion_id}/gates")
def v1_review_gates(promotion_id: str) -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    if db_path.is_file():
        with sqlite3.connect(str(db_path), timeout=10.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, catalog_id, direction, decision, gate_json FROM promotion_events WHERE id = ?",
                (promotion_id,),
            ).fetchone()
            if row:
                try:
                    gates = json.loads(row["gate_json"] or "{}")
                except Exception:
                    gates = {}
                return {
                    "promotion_id": promotion_id,
                    "catalog_id": row["catalog_id"],
                    "direction": gates.get("direction") or row["direction"],
                    "passed": bool(gates.get("passed")),
                    "failures": gates.get("failures") or [],
                    "details": gates.get("details") or {},
                    "read_only": True,
                }
    raise HTTPException(status_code=404, detail="unknown promotion")


@admin_router.post("/api/v1/review/{promotion_id}/approve")
def v1_review_approve(
    promotion_id: str, body: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if (body or {}).get("override"):
        raise HTTPException(
            status_code=403, detail="http approve cannot honor override"
        )
    db_path = _finaince_platform_db()
    if db_path.is_file():
        with sqlite3.connect(str(db_path), timeout=10.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, catalog_id, direction, decision, gate_json FROM promotion_events WHERE id = ?",
                (promotion_id,),
            ).fetchone()
            if row:
                try:
                    gates = json.loads(row["gate_json"] or "{}")
                except Exception:
                    gates = {}
                failures = gates.get("failures") or []
                if failures or not gates.get("passed", True):
                    return {
                        "ok": False,
                        "promotion_id": promotion_id,
                        "error": f"gates failed: {','.join(failures) or 'blocked'}",
                        "gates": gates,
                    }
                conn.execute(
                    "UPDATE promotion_events SET decision = 'approved' WHERE id = ?",
                    (promotion_id,),
                )
                conn.commit()
                return {
                    "ok": True,
                    "promotion_id": promotion_id,
                    "decision": "approved",
                    "gates": gates,
                }
    raise HTTPException(status_code=404, detail="unknown promotion")


@admin_router.post("/api/v1/review/{promotion_id}/reject")
def v1_review_reject(promotion_id: str) -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    if db_path.is_file():
        with sqlite3.connect(str(db_path), timeout=10.0) as conn:
            cur = conn.execute(
                "UPDATE promotion_events SET decision = 'rejected' WHERE id = ?",
                (promotion_id,),
            )
            conn.commit()
            if cur.rowcount > 0:
                return {
                    "ok": True,
                    "promotion_id": promotion_id,
                    "decision": "rejected",
                }
    raise HTTPException(status_code=404, detail="unknown promotion")


@admin_router.get("/api/v1/trace")
def v1_trace(limit: int = 50) -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    items: List[Dict[str, Any]] = []
    if db_path.is_file():
        try:
            with sqlite3.connect(str(db_path), timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, action, parent_id, job_id, cites, summary, error, metrics_json, extra_json, created_at, hypothesis FROM trace_events ORDER BY created_at DESC LIMIT ?",
                    (max(1, min(int(limit), 200)),),
                ).fetchall()
                for row in rows:
                    try:
                        metrics = json.loads(row["metrics_json"] or "{}")
                    except Exception:
                        metrics = {}
                    try:
                        extra = json.loads(row["extra_json"] or "{}")
                    except Exception:
                        extra = {}
                    items.append(
                        {
                            "id": row["id"],
                            "action": row["action"],
                            "parent_id": row["parent_id"],
                            "job_id": row["job_id"],
                            "cites": row["cites"],
                            "summary": row["summary"],
                            "error": row["error"],
                            "metrics": metrics,
                            "extra": extra,
                            "created_at": row["created_at"],
                            "hypothesis": row["hypothesis"],
                        }
                    )
        except Exception:
            pass
    return {"items": items, "count": len(items)}


@admin_router.get("/api/v1/jobs")
def v1_jobs() -> Dict[str, Any]:
    db_path = _finaince_platform_db()
    items: List[Dict[str, Any]] = []
    if db_path.is_file():
        try:
            with sqlite3.connect(str(db_path), timeout=10.0) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, kind, status, payload_json, result_json, error, engine_run_id, created_at, updated_at FROM jobs ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
                for row in rows:
                    try:
                        payload = json.loads(row["payload_json"] or "{}")
                    except Exception:
                        payload = {}
                    try:
                        result = json.loads(row["result_json"] or "{}")
                    except Exception:
                        result = {}
                    items.append(
                        {
                            "id": row["id"],
                            "kind": row["kind"],
                            "status": row["status"],
                            "payload": payload,
                            "result": result,
                            "error": row["error"],
                            "engine_run_id": row["engine_run_id"],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        }
                    )
        except Exception:
            pass
    return {"items": items, "count": len(items)}


@admin_router.get("/api/v1/jobs/{job_id}")
def v1_job_detail(job_id: str) -> Dict[str, Any]:
    for row in v1_jobs()["items"]:
        if row["id"] == job_id:
            return row
    raise HTTPException(status_code=404, detail="unknown job id")


@admin_router.get("/{full_path:path}", response_model=None)
def frontend_fallback(full_path: str):
    include_spa = os.getenv("AIMINER_INCLUDE_SPA", "1").lower() in {
        "1",
        "true",
        "yes",
    }
    if not include_spa:
        raise HTTPException(404, "spa disabled")
    if full_path.startswith("api") or full_path.startswith("ws"):
        raise HTTPException(404, "not found")
    index_path = _frontend_index_path()
    if index_path:
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return PlainTextResponse("frontend not built", status_code=404)
