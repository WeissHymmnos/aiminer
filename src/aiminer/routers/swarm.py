"""Swarm run lifecycle, orchestration, and worker management APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["swarm"])
swarm_router = router
