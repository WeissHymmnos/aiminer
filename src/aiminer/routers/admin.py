"""Admin, health check, and system readiness APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["admin"])
admin_router = router
