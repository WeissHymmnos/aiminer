"""Quant knowledge graph, wiki pages, and documentation APIRouter."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from aiminer.routers.common import *

router = APIRouter(tags=["wiki"])
wiki_router = router


@wiki_router.get("/api/wiki/index")
def wiki_index(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=LIST_PAGE_LIMIT_DEFAULT, ge=1),
) -> Dict[str, Any]:
    pages = _load_wiki_pages()
    rows = [
        {
            "slug": slug,
            "title": page["title"],
            "updated": page["updated"],
            "type": page["type"],
            "status": page["status"],
        }
        for slug, page in pages.items()
    ]
    rows.sort(key=lambda item: item.get("updated") or "", reverse=True)
    total = len(rows)
    start = max(0, offset)
    page_limit = _list_limit(limit, LIST_PAGE_LIMIT_MAX)
    end = min(total, start + page_limit)
    return {
        "items": rows[start:end],
        "total": total,
        "offset": start,
        "limit": page_limit,
        "next_offset": end,
    }


@wiki_router.get("/api/wiki/page/{slug}", response_class=PlainTextResponse)
def wiki_page(slug: str) -> PlainTextResponse:
    slug = _safe_segment(slug)
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists() or path.name in {"index.md", "log.md"}:
        raise HTTPException(404, "wiki page not found")
    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
    )


@wiki_router.get("/api/wiki/graph")
def wiki_graph() -> Dict[str, Any]:
    return _build_wiki_graph()


@wiki_router.post("/api/wiki/lint")
def wiki_lint(
    stale_days: int = 30,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    from aiminer.core.wiki import LLMWiki

    _audit(actor, "wiki.lint", "wiki", {"stale_days": stale_days})
    try:
        wiki = LLMWiki(settings=SETTINGS)
        return wiki.lint(stale_days=stale_days)
    except Exception as exc:
        raise HTTPException(500, f"lint failed: {exc}")


@wiki_router.put("/api/wiki/page/{slug}")
def wiki_update_page(
    slug: str,
    req: WikiPageUpdateRequest,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    slug = _safe_segment(slug)
    path = WIKI_DIR / f"{slug}.md"
    if path.name in {"index.md", "log.md"}:
        raise HTTPException(400, "system wiki pages are read-only")
    if not path.exists():
        raise HTTPException(404, "wiki page not found")
    meta, _body = parse_wiki_frontmatter(req.content)
    frontmatter_slug = str(meta.get("slug") or "").strip()
    if frontmatter_slug and _safe_segment(frontmatter_slug) != slug:
        raise HTTPException(400, "frontmatter slug must match requested slug")
    _audit(actor, "wiki.update", slug)
    normalized = req.content.rstrip() + "\n"
    path.write_text(normalized, encoding="utf-8")
    return {
        "status": "saved",
        "slug": slug,
        "bytes": len(normalized.encode("utf-8")),
    }


@wiki_router.post("/api/wiki/migrate")
def wiki_migrate(
    dry_run: bool = False,
    actor: Actor = Depends(_require_actor),
) -> Dict[str, Any]:
    from aiminer.core.wiki import LLMWiki

    _audit(actor, "wiki.migrate", "wiki", {"dry_run": dry_run})
    try:
        wiki = LLMWiki(settings=SETTINGS)
        return wiki.migrate_legacy_pages(dry_run=dry_run)
    except Exception as exc:
        raise HTTPException(500, f"migrate failed: {exc}")


# Backward compatibility aliases
wiki_page_detail = wiki_page
