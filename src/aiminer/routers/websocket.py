"""Real-time log streaming and WebSocket APIRouter."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from aiminer.routers.common import *

router = APIRouter(tags=["websocket"])
websocket_router = router


@websocket_router.websocket("/ws")
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
