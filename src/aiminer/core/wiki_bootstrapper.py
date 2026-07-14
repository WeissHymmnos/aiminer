from __future__ import annotations
from typing import List, Optional
from loguru import logger
from aiminer.core.wiki import LLMWiki
from aiminer.core.rag import RAGModule
from aiminer.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate


class WikiBootstrapper:
    """Responsible for converting raw RAG documents into structured Wiki pages at startup."""

    def __init__(
        self,
        wiki: LLMWiki,
        rag: RAGModule,
        provider: str = None,
        model: str = None,
        base_url: str = None,
        reasoning_effort: str = None,
    ):
        self.wiki = wiki
        self.rag = rag
        self.llm = get_llm(
            temperature=0.3,
            provider=provider,
            model_name=model,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )

    def run(self, force: bool = False):
        if self.wiki.wiki_col.count() > 0 and not force:
            logger.info(
                "Wiki already has content, skipping initialization. Use --wiki-bootstrap to force refresh."
            )
            return

        logger.info("Wiki-ifying the shared knowledge base from RAG documents...")

        # 1. Market Regime Baseline
        self._summarize_to_wiki(
            query="market metadata, current market conditions, indices information",
            slug="market_regime_base",
            title="Market Regime & Universe Baseline",
            page_type="market_profile",
            summary="Snapshot of the current market regime, universe composition, and macro conditions used as context for factor mining.",
            tags=["baseline", "market"],
        )

        # 2. Qlib Operator Reference
        self._summarize_to_wiki(
            query="Qlib alpha factors, mathematical operators signatures, formula syntax",
            slug="qlib_operator_guide",
            title="Qlib Operator & Formula Reference",
            page_type="technical_ref",
            summary="Canonical reference for supported Qlib operators, signatures, and formula syntax used by FactorAgent.",
            tags=["baseline", "reference"],
        )

        # 3. Strategy Families & Academic Base
        self._summarize_to_wiki(
            query="academic papers summaries, factor categories, momentum, value, mean reversion theories",
            slug="strategy_families_base",
            title="Alpha Strategy Families Baseline",
            page_type="strategy_family",
            summary="Taxonomy of alpha strategy families (momentum, mean-reversion, value, etc.) used as the parent category for every generated factor card.",
            tags=["baseline", "taxonomy"],
        )

        logger.success("✨ Shared knowledge base has been Wiki-ified!")

    def _summarize_to_wiki(
        self,
        query: str,
        slug: str,
        title: str,
        page_type: str,
        summary: str = "",
        tags: Optional[List[str]] = None,
    ):
        """Retrieves fragments from RAG and uses LLM to synthesize a structured Wiki page."""
        logger.info(f"Synthesizing Wiki page: {title}...")

        # Retrieve up to 5 fragments to keep synthesis focused and avoid length issues
        raw_context = self.rag.retrieve(query, n_results=5)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a senior quantitative knowledge engineer. "
                    "Your goal is to convert raw, fragmented RAG documents into a high-quality, structured Wiki page. "
                    "Use clean Markdown. Focus on hierarchical categorization and actionable insights. "
                    "Keep the output CONCISE and structured (maximum 2000 words). "
                    "Write as a permanent internal reference for other AI research agents.",
                ),
                (
                    "user",
                    "Project: {title}\n\nContext Fragments from Database:\n{context}\n\n"
                    "Synthesize a structured Wiki page for '{title}'. Include definitions, 'standard patterns', and 'cautionary notes'. "
                    "Return only the Markdown content.",
                ),
            ]
        )

        try:
            chain = prompt | self.llm
            # Pass title and context as variables to avoid curly brace interpolation issues in raw_context
            response = chain.invoke({"title": title, "context": raw_context})

            self.wiki.add_or_update_page(
                slug=slug,
                title=title,
                content=response.content,
                metadata={
                    "type": page_type,
                    "status": "baseline",
                    "summary": summary,
                    "tags": list(tags or []),
                },
            )
        except Exception as e:
            logger.error(f"Failed to synthesize Wiki page {title}: {e}")
