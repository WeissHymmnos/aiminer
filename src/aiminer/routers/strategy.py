"""Strategy optimization, backtest, and portfolio generation APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["strategy"])
strategy_router = router
