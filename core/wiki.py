import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import chromadb
from chromadb.utils.embedding_functions import (
    OpenAIEmbeddingFunction,
    SentenceTransformerEmbeddingFunction,
)
from core.llm import get_llm_config


# --- Frontmatter helpers (avoid PyYAML dep) ---

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse a minimal YAML-style frontmatter block. Supports scalar and
    flow-list values (e.g. `tags: [a, b]`). Returns (meta, body)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: Dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        if v.startswith("[") and v.endswith("]"):
            items = [s.strip().strip('"').strip("'") for s in v[1:-1].split(",")]
            meta[k] = [s for s in items if s]
        else:
            meta[k] = v.strip('"').strip("'")
    return meta, text[m.end():]


def _dump_frontmatter(meta: Dict[str, Any]) -> str:
    """Write a minimal, stable YAML-ish frontmatter block."""
    lines = ["---"]
    for k in ("title", "slug", "type", "status", "summary", "updated", "tags", "related"):
        if k not in meta:
            continue
        v = meta[k]
        if isinstance(v, (list, tuple)):
            items = ", ".join(f'"{str(x).replace(chr(34), chr(92) + chr(34))}"' for x in v)
            lines.append(f"{k}: [{items}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            safe = str(v).replace('"', '\\"').replace("\n", " ")
            lines.append(f'{k}: "{safe}"')
    # Preserve any extra keys caller passed (e.g. ic, rank_ic, iteration)
    for k, v in meta.items():
        if k in {"title", "slug", "type", "status", "summary", "updated", "tags", "related"}:
            continue
        if isinstance(v, (list, tuple)):
            items = ", ".join(f'"{x}"' for x in v)
            lines.append(f"{k}: [{items}]")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            safe = str(v).replace('"', '\\"').replace("\n", " ")
            lines.append(f'{k}: "{safe}"')
    lines.append("---")
    return "\n".join(lines) + "\n\n"


_WIKILINK_RE = re.compile(r"\[\[([A-Za-z0-9_\-]+)\]\]")


class LLMWiki:
    def __init__(self, db_dir: str = "data/wiki_db", wiki_vault: str = "data/wiki_vault", embedding_provider: str = None):
        self.wiki_vault = wiki_vault
        os.makedirs(self.wiki_vault, exist_ok=True)
        # When True, add_or_update_page skips the per-write recompile and
        # defers it to an explicit flush() call — use during batch swarm runs.
        self._batch_mode: bool = False

        # Karpathy logic: initialize core metadata files
        self.index_file = os.path.join(self.wiki_vault, "index.md")
        self.log_file = os.path.join(self.wiki_vault, "log.md")
        self._ensure_file(self.index_file, "# Wiki Index\n\nWelcome to the compiled knowledge base.\n")
        self._ensure_file(self.log_file, "# Wiki Maintenance Log\n\n")

        # ... (Previous embedding initialization remains for search speed) ...
        # [Existing embedding code here, truncated for replace call brevity]
        use_local = (embedding_provider == "local") or (
            os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true"
        )

        model_tag = "api"
        if use_local:
            model_name = "Qwen/Qwen3-Embedding-4B"
            model_tag = model_name.replace("/", "_")
            logger.info(f"Wiki: Initializing LOCAL embedding model ({model_name})...")
            self.embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=model_name, trust_remote_code=True
            )
        else:
            _EMBEDDING_DEFAULTS = {
                "kimi": {
                    "model_name": "embedding-2",
                    "api_base": "https://api.moonshot.cn/v1",
                },
                "qwen": {
                    "model_name": "text-embedding-v3",
                    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                },
                "claude": {
                    "model_name": "text-embedding-3-small",
                    "api_base": "https://api.gptsapi.net/v1",
                },
                "glm": {
                    "model_name": "embedding-3",
                    "api_base": "https://open.bigmodel.cn/api/paas/v4",
                },
                "openai": {
                    "model_name": "text-embedding-3-large",
                    "api_base": "https://api.gptsapi.net/v1",
                },
            }
            try:
                cfg = get_llm_config(provider=embedding_provider)
                provider = cfg["provider"]
                api_key = cfg["api_key"]
                emb_defaults = _EMBEDDING_DEFAULTS.get(
                    provider, _EMBEDDING_DEFAULTS["openai"]
                )

                logger.info(f"Wiki: Initializing API-based embedding ({provider})...")
                self.embedding_fn = OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=emb_defaults["model_name"],
                    api_base=emb_defaults["api_base"],
                )
                model_tag = f"{provider}_{emb_defaults['model_name'].replace('/', '_')}"
            except Exception:
                logger.warning("Wiki: Falling back to LOCAL bge-large for embeddings.")
                model_tag = "bge-large"
                self.embedding_fn = SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-large-zh-v1.5"
                )

        self.db_dir = os.path.join(db_dir, model_tag)
        os.makedirs(self.db_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_dir)
        self.wiki_col = self.client.get_or_create_collection(
            "llm_wiki", embedding_function=self.embedding_fn
        )

    def list_pages(self, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all pages in the wiki."""
        where = {"type": type_filter} if type_filter else None
        results = self.wiki_col.get(where=where, include=["documents", "metadatas"])
        
        pages = []
        if results["ids"]:
            for doc, meta in zip(results["documents"], results["metadatas"]):
                pages.append({
                    "title": meta.get("title", "Untitled"),
                    "slug": meta.get("slug", ""),
                    "type": meta.get("type", "factor_card"),
                    "last_updated": meta.get("last_updated", ""),
                    "content": doc
                })
        return pages

    # ---------------------------------------------------------------
    # Karpathy-style write path: frontmatter + log event + backlink audit
    # ---------------------------------------------------------------

    def add_or_update_page(
        self,
        slug: str,
        title: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Compile knowledge once, keep it current as a persistent artifact.

        Extended metadata keys (all optional):
          - summary  : one-line description shown in the compiled index
          - status   : 'proven' / 'failed' / 'baseline' / ...
          - tags     : list[str] — topical tags used for backlink audit
          - related  : list[str] — slugs this page explicitly relates to.
                       Each related target gets a reciprocal [[slug]] entry
                       appended under a `## Backlinks` section.
        """
        page_id = f"wiki_{slug}"
        file_path = os.path.join(self.wiki_vault, f"{slug}.md")

        # Detect whether this is an INGEST (new) or UPDATE (existing)
        is_new = not os.path.exists(file_path)
        event = "INGEST" if is_new else "UPDATE"
        now_iso = datetime.utcnow().isoformat(timespec="seconds")

        # Normalize metadata into a well-known shape
        full_meta: Dict[str, Any] = {
            "title": title,
            "slug": slug,
            "type": metadata.get("type", "factor_card"),
            "status": metadata.get("status", "draft"),
            "summary": metadata.get("summary", "") or self._derive_summary(content),
            "updated": now_iso,
            "tags": list(metadata.get("tags", []) or []),
            "related": list(metadata.get("related", []) or []),
        }
        # Keep extra scalar fields (ic, rank_ic, iteration, is_effective, ...)
        for k, v in metadata.items():
            if k in full_meta or k == "last_updated":
                continue
            full_meta[k] = v

        # 1. Write the physical Markdown file (source of truth)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(_dump_frontmatter(full_meta))
            f.write(content.rstrip() + "\n")

        # 2. Update the Shadow Index (ChromaDB)
        chroma_meta = {
            **{k: v for k, v in full_meta.items() if isinstance(v, (str, int, float, bool))},
            "last_updated": now_iso,
            "tags_str": ",".join(full_meta["tags"]),
            "related_str": ",".join(full_meta["related"]),
        }
        self.wiki_col.upsert(
            ids=[page_id],
            documents=[f"# {title}\n\n{full_meta['summary']}\n\n{content}"],
            metadatas=[chroma_meta],
        )

        # 3. Reciprocal backlink audit (Karpathy: LLMs don't mind touching
        #    15 files in one pass — but we can do it programmatically when
        #    the `related` list is explicit).
        self._backlink_audit(slug, title, full_meta["related"])

        # 4. Append event to log.md in the `## [date] event | title` format
        #    so it is grep-able with standard tools.
        self._log_event(event, slug, title, extra=full_meta.get("status"))

        # 5. Recompile the index unless batch_mode is active (caller will
        #    call flush() once after writing all pages in the batch).
        if not self._batch_mode:
            self._recompile_index()

        logger.info(f"✅ Compiled Wiki Page [{event}]: {title} ({file_path})")
        return page_id

    def flush(self):
        """Recompile the index after a batch of writes. Call this once after
        using batch_mode to avoid O(N²) recompiles during swarm runs."""
        self._recompile_index()

    @staticmethod
    def _derive_summary(content: str, max_len: int = 140) -> str:
        """Extract a one-line summary from the first non-empty, non-heading line."""
        for raw in content.splitlines():
            s = raw.strip().lstrip("#").strip()
            if not s:
                continue
            # Strip common markdown emphasis markers
            s = re.sub(r"[*_`]+", "", s)
            if len(s) > max_len:
                s = s[: max_len - 1].rstrip() + "…"
            return s
        return ""

    def _log_event(self, event: str, slug: str, title: str, extra: Optional[str] = None):
        """Append a Karpathy-style event record to log.md.

        Format: `## [YYYY-MM-DD HH:MM] EVENT | title (slug) [status]`
        The consistent prefix makes the log grep-able: `grep '^## ' log.md`.
        """
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        tail = f" [{extra}]" if extra else ""
        line = f"## [{stamp}] {event} | {title} ([[{slug}]]){tail}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def _backlink_audit(self, new_slug: str, new_title: str, related_slugs: List[str]):
        """For every slug this new page declares as `related`, reciprocate
        by appending `[[new_slug]]` under a `## Backlinks` section on that
        target page. Idempotent — skips targets that already link back.
        """
        for target in related_slugs:
            if not target or target == new_slug:
                continue
            target_path = os.path.join(self.wiki_vault, f"{target}.md")
            if not os.path.exists(target_path):
                logger.debug(
                    f"[Backlink] Target '{target}' does not exist; skipping "
                    f"reciprocal link from '{new_slug}'."
                )
                continue
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                logger.warning(f"[Backlink] Failed to read {target_path}: {e}")
                continue

            # Already linked back — skip.
            if re.search(rf"\[\[{re.escape(new_slug)}\]\]", text):
                continue

            backlink_line = f"- [[{new_slug}]] — {new_title}\n"
            if "## Backlinks" in text:
                # Append under the existing section (insert before next H2 or EOF)
                parts = text.split("## Backlinks", 1)
                head, tail = parts[0], parts[1]
                # Find the next H2 header in tail
                next_h2 = re.search(r"\n## ", tail)
                if next_h2:
                    insert_at = next_h2.start()
                    new_tail = tail[:insert_at].rstrip() + "\n" + backlink_line + tail[insert_at:]
                else:
                    new_tail = tail.rstrip() + "\n" + backlink_line
                new_text = head + "## Backlinks" + new_tail
            else:
                new_text = text.rstrip() + "\n\n## Backlinks\n\n" + backlink_line

            with open(target_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            logger.debug(f"[Backlink] {new_slug} → {target}")

    def _ensure_file(self, path, content):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def _read_page_meta(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            return {}
        meta, _ = _parse_frontmatter(text)
        return meta

    # ---------------------------------------------------------------
    # Compiled index: categorized by type, one-line summaries
    # ---------------------------------------------------------------

    def _recompile_index(self):
        """Rebuild index.md as a content-oriented catalog — pages are
        grouped by `type`, sorted by last_updated desc, and each entry
        shows its one-line summary so agents can navigate without opening
        every file."""
        exclude = {"index.md", "log.md"}
        entries: List[Dict[str, Any]] = []
        for fn in os.listdir(self.wiki_vault):
            if not fn.endswith(".md") or fn in exclude:
                continue
            path = os.path.join(self.wiki_vault, fn)
            if not os.path.isfile(path):
                continue
            meta = self._read_page_meta(path)
            slug = fn[:-3]
            entries.append({
                "slug": slug,
                "title": meta.get("title") or slug.replace("_", " "),
                "type": meta.get("type") or "uncategorized",
                "status": meta.get("status") or "",
                "summary": meta.get("summary") or "",
                "updated": meta.get("updated") or "",
            })

        # Group by type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            by_type.setdefault(e["type"], []).append(e)
        for group in by_type.values():
            group.sort(key=lambda x: x.get("updated") or "", reverse=True)

        # Stable type ordering: baselines first, then factor cards, then rest
        type_order = [
            "market_profile",
            "technical_ref",
            "strategy_family",
            "factor_card",
        ]
        ordered_types = [t for t in type_order if t in by_type] + sorted(
            [t for t in by_type if t not in type_order]
        )

        lines: List[str] = []
        lines.append("# Wiki Index (Compiled)\n")
        lines.append(
            f"*Last compiled: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} · "
            f"{len(entries)} pages across {len(by_type)} categor"
            f"{'y' if len(by_type) == 1 else 'ies'}*\n"
        )
        for t in ordered_types:
            pretty = t.replace("_", " ").title()
            lines.append(f"\n## {pretty} ({len(by_type[t])})\n")
            for e in by_type[t]:
                status = f" · `{e['status']}`" if e["status"] else ""
                summary = f" — {e['summary']}" if e["summary"] else ""
                lines.append(f"- [[{e['slug']}]] **{e['title']}**{status}{summary}")

        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # ---------------------------------------------------------------
    # One-shot migration: upgrade legacy pages to the enriched schema
    # ---------------------------------------------------------------

    def migrate_legacy_pages(self, dry_run: bool = False) -> Dict[str, Any]:
        """Rewrite legacy wiki pages (written before the enriched frontmatter
        schema landed) so they carry `slug`, `status`, `summary`, `tags`, and
        `related`. Idempotent — pages that already have all canonical fields
        are left untouched.

        Status inference:
          - `type` in {market_profile, technical_ref, strategy_family} → baseline
          - body contains "✅ EFFECTIVE" / "Effectiveness: ✅" → proven
          - body contains "❌ FAILED" / "Effectiveness: ❌" → failed
          - else → draft

        Factor cards get `related=["strategy_families_base"]` by default so
        they stop being flagged as orphans by the lint pass.
        """
        exclude = {"index.md", "log.md"}
        touched: List[str] = []
        skipped: List[str] = []
        canonical = {"title", "slug", "type", "status", "summary", "updated", "tags", "related"}

        for fn in sorted(os.listdir(self.wiki_vault)):
            if not fn.endswith(".md") or fn in exclude:
                continue
            path = os.path.join(self.wiki_vault, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                logger.warning(f"[Migrate] Failed to read {path}: {e}")
                continue

            meta, body = _parse_frontmatter(text)
            slug = fn[:-3]

            # Already fully migrated — skip.
            if canonical.issubset(meta.keys()):
                skipped.append(slug)
                continue

            page_type = meta.get("type") or "factor_card"
            title = meta.get("title") or slug.replace("_", " ").title()

            # Infer status
            status = meta.get("status")
            if not status:
                if page_type in {"market_profile", "technical_ref", "strategy_family"}:
                    status = "baseline"
                elif "✅ EFFECTIVE" in body or "Effectiveness: ✅" in body:
                    status = "proven"
                elif "❌ FAILED" in body or "Effectiveness: ❌" in body:
                    status = "failed"
                else:
                    status = "draft"

            # Derive summary if missing
            summary = meta.get("summary") or self._derive_summary(body)

            # Default related: factor cards link back to the strategy family
            # baseline so they are not lint-flagged as orphans.
            related = meta.get("related")
            if not related:
                related = ["strategy_families_base"] if page_type == "factor_card" else []

            tags = meta.get("tags") or []
            updated = meta.get("updated") or datetime.utcnow().isoformat(timespec="seconds")

            new_meta: Dict[str, Any] = {
                "title": title,
                "slug": slug,
                "type": page_type,
                "status": status,
                "summary": summary,
                "updated": updated,
                "tags": list(tags) if isinstance(tags, (list, tuple)) else [],
                "related": list(related) if isinstance(related, (list, tuple)) else [],
            }
            # Preserve any extra legacy scalar fields
            for k, v in meta.items():
                if k in new_meta or k == "last_updated":
                    continue
                new_meta[k] = v

            if dry_run:
                touched.append(slug)
                continue

            with open(path, "w", encoding="utf-8") as f:
                f.write(_dump_frontmatter(new_meta))
                f.write(body.lstrip("\n"))
            touched.append(slug)

        # Reciprocate backlinks for every migrated page so factor cards show
        # up under their parent strategy family's `## Backlinks` section.
        if not dry_run:
            for slug in touched:
                path = os.path.join(self.wiki_vault, f"{slug}.md")
                meta = self._read_page_meta(path)
                self._backlink_audit(slug, meta.get("title", slug), meta.get("related") or [])

            self._recompile_index()
            stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(
                    f"## [{stamp}] MIGRATE | upgraded {len(touched)} legacy pages "
                    f"(skipped {len(skipped)})\n"
                )

        logger.info(
            f"🔧 Wiki migration {'(dry-run) ' if dry_run else ''}complete: "
            f"{len(touched)} upgraded, {len(skipped)} already canonical"
        )
        return {
            "upgraded": touched,
            "skipped": skipped,
            "dry_run": dry_run,
        }

    # ---------------------------------------------------------------
    # Lint / health-check (Karpathy: find orphan pages, stale claims,
    # missing cross-references, contradictions)
    # ---------------------------------------------------------------

    def lint(self, stale_days: int = 30) -> Dict[str, Any]:
        """Scan the vault for structural problems. Writes a severity-tiered
        report to `.lint/lint_<date>.md` and appends a LINT entry to log.md.

        Returns the report as a dict so programmatic callers (HTTP API,
        tests) can consume it directly.
        """
        exclude = {"index.md", "log.md"}
        pages: Dict[str, Dict[str, Any]] = {}
        # Sort filenames so lint reports are deterministic across runs.
        for fn in sorted(os.listdir(self.wiki_vault)):
            if not fn.endswith(".md") or fn in exclude:
                continue
            path = os.path.join(self.wiki_vault, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            meta, body = _parse_frontmatter(text)
            slug = fn[:-3]
            pages[slug] = {
                "slug": slug,
                "meta": meta,
                "body": body,
                "path": path,
                "links": set(_WIKILINK_RE.findall(body)),
            }

        # Build inbound-link map
        inbound: Dict[str, List[str]] = {s: [] for s in pages}
        for s, p in pages.items():
            for target in p["links"]:
                if target in inbound:
                    inbound[target].append(s)

        errors: List[str] = []
        warnings: List[str] = []
        infos: List[str] = []

        cutoff = datetime.utcnow() - timedelta(days=stale_days)

        for slug, p in pages.items():
            meta = p["meta"]

            # ERROR: broken wikilinks
            for target in p["links"]:
                if target not in pages:
                    errors.append(
                        f"`{slug}` contains a broken wikilink `[[{target}]]` — target does not exist."
                    )

            # ERROR: factor card marked as proven but is_effective=false
            status = str(meta.get("status", "")).lower()
            ie_raw = str(meta.get("is_effective", "")).lower()
            if meta.get("type") == "factor_card":
                if status == "proven" and ie_raw in {"false", "0", "no"}:
                    errors.append(
                        f"`{slug}` has status=proven but is_effective=false — contradiction."
                    )
                if status == "failed" and ie_raw in {"true", "1", "yes"}:
                    errors.append(
                        f"`{slug}` has status=failed but is_effective=true — contradiction."
                    )

            # WARNING: missing summary
            if not meta.get("summary"):
                warnings.append(f"`{slug}` has no `summary` field in frontmatter.")

            # WARNING: stale page
            updated = meta.get("updated")
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated)
                    if updated_dt < cutoff:
                        warnings.append(
                            f"`{slug}` is stale — last updated {updated} ({stale_days}+ days ago)."
                        )
                except ValueError:
                    warnings.append(f"`{slug}` has unparseable `updated` field: {updated}")

            # WARNING: factor card with no parent strategy family
            if meta.get("type") == "factor_card":
                related = meta.get("related") or []
                has_family = any(
                    pages.get(r, {}).get("meta", {}).get("type") == "strategy_family"
                    for r in related
                )
                if not has_family:
                    warnings.append(
                        f"`{slug}` is a factor_card with no parent strategy_family in `related`."
                    )

            # INFO: orphan page (no inbound links AND no outbound wikilinks)
            if not inbound.get(slug) and not p["links"] and meta.get("type") != "market_profile":
                infos.append(
                    f"`{slug}` is an orphan — no incoming or outgoing wikilinks."
                )

        report = {
            "scanned_at": datetime.utcnow().isoformat(timespec="seconds"),
            "page_count": len(pages),
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
        }

        # Persist report to .lint/ (hidden so the normal wiki index glob
        # doesn't include it).
        lint_dir = os.path.join(self.wiki_vault, ".lint")
        os.makedirs(lint_dir, exist_ok=True)
        report_name = f"lint_{datetime.utcnow().strftime('%Y-%m-%d')}.md"
        report_path = os.path.join(lint_dir, report_name)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Wiki Lint Report — {report['scanned_at']}\n\n")
            f.write(f"*Scanned {report['page_count']} pages*\n\n")
            f.write(f"- 🔴 Errors: {len(errors)}\n")
            f.write(f"- 🟡 Warnings: {len(warnings)}\n")
            f.write(f"- 🔵 Info: {len(infos)}\n\n")
            if errors:
                f.write("## 🔴 Errors\n\n")
                for e in errors:
                    f.write(f"- {e}\n")
                f.write("\n")
            if warnings:
                f.write("## 🟡 Warnings\n\n")
                for w in warnings:
                    f.write(f"- {w}\n")
                f.write("\n")
            if infos:
                f.write("## 🔵 Info\n\n")
                for i in infos:
                    f.write(f"- {i}\n")
                f.write("\n")
            if not (errors or warnings or infos):
                f.write("_Wiki is clean — no issues found._\n")
        report["report_path"] = report_path

        # Log the lint pass
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(
                f"## [{stamp}] LINT | scanned {report['page_count']} pages "
                f"(🔴 {len(errors)} / 🟡 {len(warnings)} / 🔵 {len(infos)})\n"
            )

        logger.info(
            f"🧹 Wiki lint complete: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} infos → {report_path}"
        )
        return report

    # ---------------------------------------------------------------
    # Full-page query (vs. the truncated `retrieve` used for context)
    # ---------------------------------------------------------------

    def query_pages(
        self,
        query: str,
        top_k: int = 3,
        type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search that returns full pages (frontmatter + body)
        instead of truncated snippets. Use this when the caller wants to
        reason over complete wiki content rather than paste it as context."""
        try:
            count = self.wiki_col.count()
            if count == 0:
                return []
            where = {"type": type_filter} if type_filter else None
            actual_k = min(top_k, count)
            results = self.wiki_col.query(
                query_texts=[query], n_results=actual_k, where=where
            )
        except Exception as e:
            logger.error(f"Wiki query_pages failed: {e}")
            return []

        out: List[Dict[str, Any]] = []
        if not results.get("documents") or not results["documents"][0]:
            return out
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            slug = meta.get("slug")
            if not slug:
                continue
            # Parse frontmatter+body from the filesystem file (source of truth).
            path = os.path.join(self.wiki_vault, f"{slug}.md")
            body = ""
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
                _, body = _parse_frontmatter(raw)
            out.append({
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", ""),
                "status": meta.get("status", ""),
                "summary": meta.get("summary", ""),
                "last_updated": meta.get("last_updated", ""),
                "body": body,
                "chroma_meta": meta,
                "chroma_doc": doc,
            })
        return out

    def retrieve(
        self, query: str, n_results: int = 3, type_filter: Optional[str] = None
    ) -> str:
        """从 Wiki 检索"""
        try:
            count = self.wiki_col.count()
            if count == 0:
                return "Wiki 中暂无相关知识。"

            actual_n = min(n_results, count)
            where = {"type": type_filter} if type_filter else None

            results = self.wiki_col.query(
                query_texts=[query], n_results=actual_n, where=where
            )

            if not results["documents"] or not results["documents"][0]:
                return "Wiki 中暂无相关匹配内容。"

            parts = ["=== LLM WIKI ==="]
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                meta = meta or {}
                title = meta.get("title") or meta.get("slug") or "Untitled"
                updated = meta.get("updated") or meta.get("last_updated") or ""
                updated_short = updated[:10] if isinstance(updated, str) else ""
                parts.append(f"**{title}** (更新于 {updated_short})")
                parts.append(
                    f"Type: {meta.get('type', '')}, Status: {meta.get('status', '')}"
                )
                parts.append(doc[:1000] + "..." if len(doc) > 1000 else doc)
                parts.append("---")
            return "\n".join(parts)
        except Exception as e:
            logger.error(f"Wiki 查询失败: {e}")
            return "Wiki 查询出错"

    def get_page(self, slug: str) -> Optional[Dict]:
        """获取单个页面"""
        results = self.wiki_col.get(where={"slug": slug})
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "title": results["metadatas"][0]["title"],
                "content": results["documents"][0],
                "metadata": results["metadatas"][0],
            }
        return None
