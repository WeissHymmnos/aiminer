"""Unit tests for modular APIRouters."""

from __future__ import annotations

from fastapi import APIRouter

import aiminer.api as api
from aiminer.routers import (
    admin_router,
    backtest_router,
    strategy_router,
    swarm_router,
    websocket_router,
    wiki_router,
)


def test_api_routers_importable():
    assert isinstance(admin_router, APIRouter)
    assert isinstance(backtest_router, APIRouter)
    assert isinstance(strategy_router, APIRouter)
    assert isinstance(swarm_router, APIRouter)
    assert isinstance(wiki_router, APIRouter)
    assert isinstance(websocket_router, APIRouter)


def test_api_routers_backward_compatibility_namespace():
    import aiminer.api.routers as api_routers
    from aiminer.api.routers import (
        admin,
        backtest,
        strategy,
        swarm,
        websocket,
        wiki,
    )

    assert hasattr(api_routers, "admin_router")
    assert hasattr(admin, "router")
    assert hasattr(backtest, "router")
    assert hasattr(strategy, "router")
    assert hasattr(swarm, "router")
    assert hasattr(websocket, "router")
    assert hasattr(wiki, "router")


def test_app_includes_router_routes():
    route_paths = [getattr(r, "path", None) for r in api.app.routes]

    # Admin routes
    assert "/api/health" in route_paths
    assert "/api/readiness" in route_paths

    # Backtest / Factor routes
    assert "/api/results" in route_paths
    assert "/api/backtest/run" in route_paths

    # Strategy routes
    assert "/api/strategies" in route_paths
    assert "/api/strategy/run" in route_paths

    # Swarm routes
    assert "/api/swarm/status" in route_paths
    assert "/api/swarm/runs" in route_paths

    # Wiki routes
    assert "/api/wiki/index" in route_paths
    assert "/api/wiki/graph" in route_paths
