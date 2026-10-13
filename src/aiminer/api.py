"""AI Alpha Miner Web API entrypoint.

This module sets up the FastAPI application, mounts modular APIRouters,
configures CORS and static assets, and re-exports all endpoints, models,
and utilities for backward compatibility.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if "aiminer.routers.common" in sys.modules:
    importlib.reload(sys.modules["aiminer.routers.common"])
    for _sub in ("admin", "backtest", "strategy", "swarm", "wiki", "websocket"):
        _modname = f"aiminer.routers.{_sub}"
        if _modname in sys.modules:
            importlib.reload(sys.modules[_modname])
    if "aiminer.routers" in sys.modules:
        importlib.reload(sys.modules["aiminer.routers"])

import aiminer.routers as routers
from aiminer.routers import (
    admin,
    admin_router,
    backtest,
    backtest_router,
    common,
    strategy,
    strategy_router,
    swarm,
    swarm_router,
    websocket,
    websocket_router,
    wiki,
    wiki_router,
)
from aiminer.routers.common import *

# Backward-compatibility for callers importing aiminer.api.routers
sys.modules.setdefault("aiminer.api.routers", routers)
sys.modules.setdefault("aiminer.api.routers.admin", admin)
sys.modules.setdefault("aiminer.api.routers.backtest", backtest)
sys.modules.setdefault("aiminer.api.routers.strategy", strategy)
sys.modules.setdefault("aiminer.api.routers.swarm", swarm)
sys.modules.setdefault("aiminer.api.routers.websocket", websocket)
sys.modules.setdefault("aiminer.api.routers.wiki", wiki)
sys.modules.setdefault("aiminer.api.routers.common", common)


class _ApiModule(types.ModuleType):
    """Dynamic module wrapper syncing monkeypatched attributes to submodules."""

    _syncing: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name.startswith("__") or name == "_syncing":
            return
        if getattr(self, "_syncing", False):
            return
        try:
            super().__setattr__("_syncing", True)
            for submod in (
                common,
                admin,
                backtest,
                strategy,
                swarm,
                wiki,
                websocket,
            ):
                if hasattr(submod, name):
                    setattr(submod, name, value)
        finally:
            super().__setattr__("_syncing", False)


sys.modules[__name__].__class__ = _ApiModule

# Re-export route handlers
from aiminer.routers.admin import (
    admin_reset,
    frontend_fallback,
    health,
    read_index,
    readiness,
)
from aiminer.routers.backtest import (
    backtest_delete,
    backtest_get,
    backtest_history,
    backtest_run,
    backtest_validate,
    delete_backtest_job,
    get_backtest_history,
    get_backtest_job,
    get_chart,
    get_factor_chart,
    get_factor_detail,
    get_factor_report,
    get_report,
    get_results,
    run_backtest,
    run_factor_crossover,
    validate_backtest,
)
from aiminer.routers.strategy import (
    delete_strategy,
    get_strategies,
    get_strategy,
    get_strategy_chart,
    get_strategy_detail,
    get_strategy_history,
    list_strategies,
    run_strategy,
    run_strategy_backtest,
    strategy_history,
    strategy_run,
)
from aiminer.routers.swarm import (
    delete_swarm_run,
    get_swarm_run,
    get_swarm_run_logs,
    list_swarm_runs,
    start_swarm,
    stop_swarm,
    swarm_status,
)
from aiminer.routers.websocket import websocket_endpoint
from aiminer.routers.wiki import (
    wiki_graph,
    wiki_index,
    wiki_lint,
    wiki_migrate,
    wiki_page,
    wiki_page_detail,
    wiki_update_page,
)

app = FastAPI(title="AIMiner Alpha Workstation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

if FRONTEND_DIST_DIR:
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets", StaticFiles(directory=str(assets_dir)), name="assets"
        )


@app.on_event("startup")
async def startup_event() -> None:
    _ensure_runtime_dirs()
    if DB_PATH.exists():
        with _db_connect() as conn:
            _ensure_db_schema(conn)
    state.loop = asyncio.get_running_loop()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    _shutdown_active_swarm_runs()
    with state.lock:
        state.sockets.clear()
        state.loop = None


app.include_router(backtest.backtest_router)
app.include_router(strategy.strategy_router)
app.include_router(swarm.swarm_router)
app.include_router(wiki.wiki_router)
app.include_router(websocket.websocket_router)
app.include_router(admin.admin_router)


# --- Application Entry Point ---
def main():
    import multiprocessing

    import uvicorn

    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
