import re
from aiminer.core.rag import RAGModule
from aiminer.core.wiki import LLMWiki
from aiminer.core.template_renderer import TemplateRenderer
from aiminer.core.settings import AiminerSettings, build_settings
from typing import Any, Dict, List, Optional
from loguru import logger


class HybridKnowledge:
    def __init__(
        self,
        rebuild_rag: bool = False,
        embedding_provider: str = None,
        use_gpu: bool = False,
        llm_provider: str = None,
        llm_model: str = None,
        llm_base_url: str = None,
        llm_reasoning_effort: str = None,
        settings: AiminerSettings | None = None,
    ):
        self.settings = settings or build_settings(
            {
                "rebuild_rag": rebuild_rag,
                "embedding_provider": embedding_provider,
                "use_gpu": use_gpu,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "llm_base_url": llm_base_url,
                "llm_reasoning_effort": llm_reasoning_effort,
            }
        )
        self.rag = RAGModule(
            rebuild=self.settings.rebuild_rag,
            embedding_provider=self.settings.embedding_provider,
            use_gpu=self.settings.use_gpu,
            settings=self.settings,
        )
        self.wiki = LLMWiki(
            embedding_provider=self.settings.embedding_provider, settings=self.settings
        )
        self.templates = TemplateRenderer()
        self.llm_provider = self.settings.llm_provider
        self.llm_model = self.settings.llm_model
        self.llm_base_url = self.settings.llm_base_url
        self.llm_reasoning_effort = self.settings.llm_reasoning_effort

    def bootstrap_wiki(self, force: bool = False):
        """Manually trigger the Wiki-ification process from RAG docs."""
        from aiminer.core.wiki_bootstrapper import WikiBootstrapper

        bootstrapper = WikiBootstrapper(
            self.wiki,
            self.rag,
            provider=self.llm_provider,
            model=self.llm_model,
            base_url=self.llm_base_url,
            reasoning_effort=self.llm_reasoning_effort,
        )
        bootstrapper.run(force=force)

    def retrieve(self, query: str, n_results: int = 3) -> str:
        """Retrieve from both RAG (raw corpus) and Wiki (compiled knowledge).

        The compiled wiki takes precedence: when a RAG snippet and a wiki
        page share the same title (case-insensitive substring match), the
        RAG duplicate is dropped. This avoids agents seeing the same
        concept twice in their context window.
        """
        rag_context = self.rag.retrieve(query, n_results) or ""
        wiki_context = self.wiki.retrieve(query, n_results) or ""

        # Cheap dedup: collect wiki titles, drop any RAG line whose
        # normalized form contains one of them.
        wiki_titles: List[str] = []
        for line in wiki_context.splitlines():
            m = re.match(r"\*\*(.+?)\*\*", line.strip())
            if m:
                wiki_titles.append(m.group(1).strip().lower())

        if wiki_titles:
            kept = []
            for line in rag_context.splitlines():
                low = line.lower()
                if any(t in low for t in wiki_titles):
                    continue
                kept.append(line)
            rag_context = "\n".join(kept)

        # Put compiled wiki first — it is higher signal per token.
        return f"{wiki_context}\n\n{rag_context}".strip()

    def query_wiki_pages(
        self, query: str, top_k: int = 3, type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Passthrough for callers that want full wiki pages instead of
        the truncated `retrieve()` format — used by the HTTP search API."""
        return self.wiki.query_pages(query, top_k=top_k, type_filter=type_filter)

    def lint_wiki(self, stale_days: int = 30) -> Dict[str, Any]:
        """Trigger a wiki lint pass and return the structured report."""
        return self.wiki.lint(stale_days=stale_days)

    def update_wiki_after_eval(self, state: Dict[str, Any]):
        """Auto-update the LLM Wiki after a factor eval.

        Writes an `experiment_card` page linked back to the concept graph
        baseline (so factor cards are not orphans) and tagged with the
        evaluation mode and the sub-agent's role so lint/index/backlink
        audits can group related cards later.
        """
        metrics = state.get("backtest_metrics") or {}
        if (
            state.get("evaluation_failed")
            or state.get("_evaluation_failed")
            or metrics.get("evaluation_failed")
            or metrics.get("_evaluation_failed")
        ):
            logger.warning(
                "[HybridKnowledge] Skipping Wiki update: evaluation failed."
            )
            return {}

        is_simulated = state.get("is_simulated", False)
        if is_simulated:
            logger.warning(
                "[HybridKnowledge] Factor was simulated — writing to Wiki with 'simulated' flag."
            )

        try:
            # Create a slug from hypothesis name, include iteration to avoid collisions
            raw_name = state.get("hypothesis_name", "Unnamed_Factor")
            base_slug = "".join([c if c.isalnum() else "_" for c in raw_name]).lower()
            iteration = state.get("iteration", 0)
            slug = (
                f"{base_slug}_iter{iteration}"
                if base_slug
                else f"factor_iter{iteration}"
            )

            title = state.get("hypothesis_name", "Unnamed Factor")

            ic = float(metrics.get("information_coefficient", 0.0) or 0.0)
            rank_ic = float(metrics.get("rank_ic", 0.0) or 0.0)
            is_effective = bool(state.get("is_effective", False))

            hypothesis_desc = state.get("hypothesis_description", "") or ""
            summary = hypothesis_desc.strip().replace("\n", " ")
            if len(summary) > 160:
                summary = summary[:159].rstrip() + "…"
            if not summary:
                summary = f"{title} (IC {ic:.4f} / RankIC {rank_ic:.4f})"

            # Tags derive from the role prompt + evaluation mode so linting
            # can later cluster cards by their originating expert.
            role_prompt = (state.get("role_prompt") or "").strip()
            tags: List[str] = []
            if role_prompt:
                tags.append(role_prompt[:40])
            eval_mode = state.get("evaluation_mode")
            if eval_mode:
                tags.append(eval_mode)
            if is_simulated:
                tags.append("simulated")

            # Link back to the bootstrapped baseline pages so factor cards
            # are not orphans. `_backlink_audit` will reciprocate.
            related = [
                "strategy_families_base",
                "market_regime_base",
                "information_coefficient_metric",
                "rank_ic_metric",
                "price_volume_data_source",
                "cross_sectional_long_short_execution",
            ]

            content = (
                f"**Hypothesis**: {hypothesis_desc}\n\n"
                f"**Rationale**: {state.get('rationale', '')}\n\n"
                f"**Implementation (Qlib)**: `{state.get('code_expression', '')}`\n\n"
                f"**Math Formula**: {state.get('math_formula', '')}\n\n"
                f"**IC / RankIC**: {ic:.4f} / {rank_ic:.4f}\n\n"
                f"**Effectiveness**: {'✅ EFFECTIVE' if is_effective else '❌ FAILED'}\n\n"
                f"**Review Summary**: {state.get('review_summary', '')}\n\n"
                f"**Suggested Improvements**: {state.get('suggested_improvements', 'None')}\n"
            )

            self.wiki.add_or_update_page(
                slug=slug,
                title=title,
                content=content,
                metadata={
                    "type": "experiment_card",
                    "node_type": "factor_experiment",
                    "status": "active" if is_effective else "failed",
                    "evidence_level": "simulated" if is_simulated else ("validated" if is_effective else "theory"),
                    "summary": summary,
                    "tags": tags,
                    "parents": ["stat_arb_family"],
                    "depends_on": [
                        "price_volume_data_source",
                        "cross_sectional_long_short_execution",
                    ],
                    "risk_flags": ["simulation_only_risk"] if is_simulated else [],
                    "metrics_ref": ["information_coefficient_metric", "rank_ic_metric"],
                    "related": related,
                    "ic": ic,
                    "rank_ic": rank_ic,
                    "iteration": iteration,
                    "is_effective": is_effective,
                    "simulated": is_simulated,
                },
            )
            best_strategy = state.get("best_strategy_result") or {}
            if best_strategy and best_strategy.get("strategy_id") and (best_strategy.get("metrics") or best_strategy.get("strategy_config")):
                strategy_slug = f"{slug}_strategy"
                strategy_metrics = best_strategy.get("metrics") or {}
                strategy_summary = (
                    f"{best_strategy.get('label') or best_strategy.get('template_name') or 'strategy'} "
                    f"(Sharpe {float(strategy_metrics.get('sharpe', 0.0) or 0.0):.4f}, "
                    f"AR {float(strategy_metrics.get('annualized_return', 0.0) or 0.0):.4f})"
                )
                strategy_content = (
                    f"**Source Factor**: [[{slug}]]\n\n"
                    f"**Execution Style**: {state.get('execution_style', '')}\n\n"
                    f"**Strategy Config**: {best_strategy.get('strategy_config', {})}\n\n"
                    f"**Metrics**: {strategy_metrics}\n\n"
                    f"**Trade Stats**: {best_strategy.get('trade_stats', {})}\n\n"
                    f"**Rationale**: {best_strategy.get('rationale', '')}\n"
                )
                self.wiki.add_or_update_page(
                    slug=strategy_slug,
                    title=f"{title} Strategy",
                    content=strategy_content,
                    metadata={
                        "type": "strategy_experiment",
                        "node_type": "execution_strategy",
                        "status": "active" if is_effective else "failed",
                        "summary": strategy_summary,
                        "tags": [*tags, "strategy"],
                        "parents": [slug],
                        "related": [slug, *related],
                        "market_profile": state.get("market_profile"),
                        "data_backend": state.get("data_backend"),
                        "selection_score": state.get("selection_score", 0.0),
                    },
                )
            return {}  # Side effect only
        except Exception as e:
            logger.error(f"Failed to update Wiki: {e}")
            return {}
