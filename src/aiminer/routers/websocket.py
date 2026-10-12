"""Real-time log streaming and WebSocket APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["websocket"])
websocket_router = router
