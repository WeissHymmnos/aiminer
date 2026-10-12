"""Modular APIRouter definitions for AI Alpha Miner."""

from __future__ import annotations

from aiminer.routers import (
    admin,
    backtest,
    common,
    strategy,
    swarm,
    websocket,
    wiki,
)
from aiminer.routers.admin import admin_router
from aiminer.routers.backtest import backtest_router
from aiminer.routers.strategy import strategy_router
from aiminer.routers.swarm import swarm_router
from aiminer.routers.websocket import websocket_router
from aiminer.routers.wiki import wiki_router

__all__ = [
    "admin",
    "admin_router",
    "backtest",
    "backtest_router",
    "common",
    "strategy",
    "strategy_router",
    "swarm",
    "swarm_router",
    "websocket",
    "websocket_router",
    "wiki",
    "wiki_router",
]
