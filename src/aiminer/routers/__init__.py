"""Modular APIRouter definitions for AI Alpha Miner."""

from __future__ import annotations

from aiminer.routers.admin import admin_router
from aiminer.routers.backtest import backtest_router
from aiminer.routers.strategy import strategy_router
from aiminer.routers.swarm import swarm_router
from aiminer.routers.websocket import websocket_router
from aiminer.routers.wiki import wiki_router

__all__ = [
    "admin_router",
    "backtest_router",
    "strategy_router",
    "swarm_router",
    "websocket_router",
    "wiki_router",
]
