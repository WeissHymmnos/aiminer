"""Quant knowledge graph, wiki pages, and documentation APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["wiki"])
wiki_router = router
