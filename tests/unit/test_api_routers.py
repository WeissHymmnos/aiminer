"""Unit tests for modular APIRouters."""

from __future__ import annotations

from fastapi import APIRouter

import aiminer.api as api
from aiminer.routers import (
    admin,
    admin_router,
    backtest,
    backtest_router,
    strategy,
    strategy_router,
    swarm,
    swarm_router,
    websocket,
    websocket_router,
    wiki,
    wiki_router,
)


def test_api_routers_importable():
    assert isinstance(admin_router, APIRouter)
    assert isinstance(backtest_router, APIRouter)
    assert isinstance(strategy_router, APIRouter)
    assert isinstance(swarm_router, APIRouter)
    assert isinstance(wiki_router, APIRouter)
    assert isinstance(websocket_router, APIRouter)


def test_api_routers_have_routes_standalone():
    """Verify that routers actually define their routes within the module."""
    assert len(admin_router.routes) >= 4
    assert len(backtest_router.routes) >= 9
    assert len(strategy_router.routes) >= 5
    assert len(swarm_router.routes) >= 6
    assert len(wiki_router.routes) >= 5
    assert len(websocket_router.routes) >= 1


def test_router_modules_contain_callable_handlers():
    """Verify endpoints exist on router modules directly."""
    assert callable(admin.health)
    assert callable(admin.readiness)
    assert callable(backtest.run_backtest)
    assert callable(backtest.get_results)
    assert callable(strategy.run_strategy)
    assert callable(strategy.get_strategies)
    assert callable(swarm.start_swarm)
    assert callable(swarm.stop_swarm)
    assert callable(wiki.wiki_index)
    assert callable(wiki.wiki_graph)
    assert callable(websocket.websocket_endpoint)


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


def _extract_route_paths(app) -> set[str]:
    paths: set[str] = set()

    def _visit(item):
        if item is None:
            return
        if hasattr(item, "routes") and item.routes is not None:
            for sub in item.routes:
                _visit(sub)
            return

        if hasattr(item, "effective_route_contexts") and callable(
            item.effective_route_contexts
        ):
            try:
                for ctx in item.effective_route_contexts():
                    p = getattr(ctx, "path", getattr(ctx, "path_format", None))
                    if p:
                        paths.add(p)
            except Exception:
                pass

        if hasattr(item, "original_router") and hasattr(
            item.original_router, "routes"
        ):
            for sub in item.original_router.routes:
                _visit(sub)

        if hasattr(item, "app") and hasattr(item.app, "routes"):
            for sub in item.app.routes:
                _visit(sub)

        path = getattr(item, "path", getattr(item, "path_format", None))
        if path:
            paths.add(path)

    _visit(app)
    return paths


def test_app_includes_router_routes():
    route_paths = _extract_route_paths(api.app)

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
