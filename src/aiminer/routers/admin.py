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
