"""Backtest execution, factor pool, and performance analysis APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["backtest", "factors"])
backtest_router = router
