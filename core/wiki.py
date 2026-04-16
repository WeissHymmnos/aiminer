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

GRAPH_NODE_TYPES = {
    "strategy_family",
    "signal_primitive",
    "market_regime",
    "data_source",
    "risk_pattern",
    "evaluation_metric",
    "execution_pattern",
    "experiment_card",
}

LEGACY_TYPE_MAP = {
    "factor_card": "experiment_card",
    "market_profile": "market_regime",
    "technical_ref": "signal_primitive",
}

EVIDENCE_LEVELS = {"baseline", "theory", "simulated", "validated", "production"}
TAXONOMY_SLUGS = {
    "strategy_family": "taxonomy_strategy_families",
    "signal_primitive": "taxonomy_signal_primitives",
    "market_regime": "taxonomy_market_regimes",
    "data_source": "taxonomy_data_sources",
    "risk_pattern": "taxonomy_risk_patterns",
    "evaluation_metric": "taxonomy_evaluation_metrics",
    "execution_pattern": "taxonomy_execution_patterns",
    "experiment_card": "taxonomy_experiment_cards",
}

CONCEPT_LIBRARY = {
    "strategy_family": {
        "mean_reversion_family": {
            "title": "Mean Reversion Family",
            "summary": "Signals that exploit temporary dislocations and convergence back toward equilibrium or fair anchors.",
            "body": "## Definition\n\nMean reversion strategies buy temporary dislocations that are expected to normalize.\n\n## Typical Inputs\n\n- Short-horizon returns\n- VWAP deviation\n- Liquidity imbalance\n- Residual spreads\n\n## Common Failure Modes\n\n- Structural breaks\n- Fundamental repricing\n- Liquidity vacuum persistence\n",
        },
        "momentum_family": {
            "title": "Momentum Family",
            "summary": "Signals that extrapolate persistent trends or cross-sectional relative strength over a holding horizon.",
            "body": "## Definition\n\nMomentum strategies assume return persistence across time or across assets.\n\n## Typical Inputs\n\n- Multi-horizon returns\n- Volume confirmation\n- Trend filters\n- Regime persistence\n\n## Common Failure Modes\n\n- Violent reversal regimes\n- Crowding\n- Over-extended trend exhaustion\n",
        },
        "stat_arb_family": {
            "title": "Statistical Arbitrage Family",
            "summary": "Signals that exploit residual mispricing, cross-sectional dispersion, or co-movement breakdowns.",
            "body": "## Definition\n\nStat-arb strategies lean on relative value, residual convergence, and diversification across many small opportunities.\n\n## Typical Inputs\n\n- Cross-sectional ranks\n- Residual spreads\n- Sector-neutral returns\n- Correlation and covariance structure\n\n## Common Failure Modes\n\n- Correlation regime break\n- Cost drag from turnover\n- Hidden factor crowding\n",
        },
    },
    "signal_primitive": {
        "volume_divergence_signal": {
            "title": "Volume Divergence Signal Primitive",
            "summary": "Captures disagreement between price move magnitude and the quality or direction of accompanying volume.",
            "body": "## Definition\n\nVolume divergence signals look for price moves that are poorly confirmed by trading activity.\n\n## Typical Expressions\n\n- Price change scaled by rolling volume\n- Correlation between ranked price and ranked volume\n- Volume shock without confirming trend persistence\n",
        },
        "vwap_anchor_signal": {
            "title": "VWAP Anchor Signal Primitive",
            "summary": "Uses VWAP as an intraday or short-horizon fair-value anchor for reversals and continuation filters.",
            "body": "## Definition\n\nVWAP-anchor signals treat VWAP as a reference for execution pressure and mean reversion.\n\n## Typical Expressions\n\n- Close-to-VWAP deviation\n- VWAP slope or basis\n- Return strength conditional on VWAP distance\n",
        },
        "hurst_filter_signal": {
            "title": "Hurst Filter Signal Primitive",
            "summary": "Uses Hurst or persistence proxies to gate whether a signal should be interpreted as trend or reversion.",
            "body": "## Definition\n\nHurst-based filters classify when local price dynamics are persistent versus mean-reverting.\n\n## Typical Expressions\n\n- (1 - Hurst) reversion gates\n- Hurst-scaled return shocks\n- Hurst-conditioned liquidity signals\n",
        },
        "qlib_operator_guide": {
            "title": "Qlib Operator & Formula Reference",
            "summary": "Reference page for formula syntax and operator semantics used by the expression engine.",
            "body": "## Purpose\n\nCanonical operator semantics for expression generation, validation, and debugging.\n",
        },
    },
    "market_regime": {
        "market_regime_base": {
            "title": "Market Regime & Universe Baseline",
            "summary": "Baseline page for universe selection and regime labelling assumptions.",
            "body": "## Role\n\nDefines universe and regime state before modelling begins.\n",
        },
        "high_volatility_regime": {
            "title": "High Volatility Regime",
            "summary": "Periods where realized or implied volatility is elevated and liquidity thins materially.",
            "body": "## Definition\n\nHigh-volatility regimes often amplify reversal, liquidity and execution effects while degrading naive trend extrapolation.\n",
        },
        "policy_pivot_regime": {
            "title": "Policy Pivot Regime",
            "summary": "Regime where central bank stance shifts or is perceived to shift, causing cross-asset repricing.",
            "body": "## Definition\n\nPolicy pivot regimes matter for sector rotation, inflation-beta reversal and macro-sensitive signals.\n",
        },
    },
    "data_source": {
        "price_volume_data_source": {
            "title": "Price and Volume Data Source",
            "summary": "Daily OHLCV and derived intraday anchors such as VWAP form the base layer for most experiments.",
            "body": "## Included Fields\n\n- $open\n- $high\n- $low\n- $close\n- $volume\n- $vwap\n",
        },
        "macro_data_source": {
            "title": "Macro Data Source",
            "summary": "Macro indicators and rate/inflation proxies used to contextualize or modulate factor signals.",
            "body": "## Examples\n\n- inflation expectations\n- yield moves\n- policy surprises\n- trade and growth indicators\n",
        },
        "sector_data_source": {
            "title": "Sector and Cross-Sectional Aggregate Data Source",
            "summary": "Sector-level returns, realized volatility, and peer aggregates used for neutralization and cross-sectional context.",
            "body": "## Examples\n\n- sector return\n- sector realized volatility\n- sector-relative ranking\n",
        },
    },
    "risk_pattern": {
        "simulation_only_risk": {
            "title": "Simulation-Only Evidence Risk",
            "summary": "Results that appear promising but only exist on simulated or fallback metrics.",
            "body": "## Definition\n\nSimulated evidence should not be mixed with validated empirical evidence when prioritizing signals.\n",
        },
        "implementation_drift_risk": {
            "title": "Implementation Drift Risk",
            "summary": "The implemented expression deviates materially from the economic hypothesis or math formula.",
            "body": "## Definition\n\nImplementation drift is present when the code uses different fields, windows or operators than the stated hypothesis.\n",
        },
        "turnover_explosion_risk": {
            "title": "Turnover Explosion Risk",
            "summary": "A strategy's gross alpha is overwhelmed by trading costs due to unstable or excessively reactive signals.",
            "body": "## Definition\n\nTurnover explosion typically arises from threshold jitter, unstable ranks, or unbounded execution frequency.\n",
        },
    },
    "evaluation_metric": {
        "information_coefficient_metric": {
            "title": "Information Coefficient Reference",
            "summary": "Defines IC and its interpretation in factor research.",
            "body": "## Definition\n\nIC measures cross-sectional correlation between factor values and next-period returns.\n",
        },
        "rank_ic_metric": {
            "title": "Rank IC Reference",
            "summary": "Defines Rank IC and when it is preferable to raw IC.",
            "body": "## Definition\n\nRank IC focuses on ordinal monotonicity rather than linear magnitude.\n",
        },
        "strategy_risk_metrics_reference": {
            "title": "Strategy Risk Metrics Reference",
            "summary": "Reference for Sharpe, max drawdown, turnover and cost drag used in strategy evaluation.",
            "body": "## Included Metrics\n\n- Sharpe\n- Max Drawdown\n- Turnover\n- Cost Drag\n- Annualized Return\n",
        },
    },
    "execution_pattern": {
        "cross_sectional_long_short_execution": {
            "title": "Cross-Sectional Long-Short Execution Pattern",
            "summary": "Portfolio construction pattern that ranks a universe and takes balanced long/short exposure.",
            "body": "## Pattern\n\nRank the cross-section, buy the strongest signals, short the weakest, normalize exposure, and rebalance on a fixed schedule.\n",
        },
        "long_only_selection_execution": {
            "title": "Long-Only Selection Execution Pattern",
            "summary": "Pattern that holds only the highest conviction longs and leaves the rest uninvested.",
            "body": "## Pattern\n\nSelect the top tail of the ranked universe and size positions under weight and count constraints.\n",
        },
        "threshold_timing_execution": {
            "title": "Threshold Timing Execution Pattern",
            "summary": "Pattern that opens and closes positions when a signal crosses defined thresholds.",
            "body": "## Pattern\n\nUse long, short and exit thresholds to translate a continuous signal into trading states.\n",
        },
    },
}


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

    def _canonical_type(self, page_type: str) -> str:
        return LEGACY_TYPE_MAP.get(page_type, page_type)

    def _scan_pages(self, include_system: bool = False) -> Dict[str, Dict[str, Any]]:
        exclude = set() if include_system else {"index.md", "log.md"}
        pages: Dict[str, Dict[str, Any]] = {}
        for fn in sorted(os.listdir(self.wiki_vault)):
            if not fn.endswith(".md") or fn in exclude:
                continue
            path = os.path.join(self.wiki_vault, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue
            meta, body = _parse_frontmatter(raw)
            slug = fn[:-3]
            meta["type"] = self._canonical_type(meta.get("type", "experiment_card"))
            pages[slug] = {"slug": slug, "path": path, "meta": meta, "body": body}
        return pages

    def _ensure_graph_pages(self):
        for node_type, concepts in CONCEPT_LIBRARY.items():
            for slug, spec in concepts.items():
                path = os.path.join(self.wiki_vault, f"{slug}.md")
                if os.path.exists(path):
                    continue
                self.add_or_update_page(
                    slug=slug,
                    title=spec["title"],
                    content=spec["body"],
                    metadata={
                        "type": node_type,
                        "node_type": node_type,
                        "status": "active",
                        "evidence_level": "baseline" if node_type != "experiment_card" else "theory",
                        "summary": spec["summary"],
                        "canonical": True,
                        "parents": [],
                        "depends_on": [],
                        "risk_flags": [],
                        "metrics_ref": [],
                        "related": [],
                    },
                )

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")

    def _extract_experiment_sections(self, body: str) -> Dict[str, str]:
        labels = [
            "Hypothesis",
            "Rationale",
            "Implementation (Qlib)",
            "Math Formula",
            "IC / RankIC",
            "Effectiveness",
            "Review Summary",
            "Suggested Improvements",
        ]
        sections: Dict[str, str] = {}
        for label in labels:
            match = re.search(
                rf"\*\*{re.escape(label)}\*\*:\s*(.*?)(?=\n\*\*|\n## |\Z)",
                body,
                re.DOTALL,
            )
            sections[label] = match.group(1).strip() if match else ""
        return sections

    def _infer_graph_metadata(
        self, slug: str, meta: Dict[str, Any], body: str, sections: Dict[str, str]
    ) -> Dict[str, Any]:
        text = " ".join(
            [
                slug,
                meta.get("title", ""),
                meta.get("summary", ""),
                body,
                sections.get("Implementation (Qlib)", ""),
                sections.get("Rationale", ""),
                sections.get("Review Summary", ""),
                sections.get("Suggested Improvements", ""),
            ]
        ).lower()

        families = []
        if any(k in text for k in ["reversion", "mean-reversion", "reversal"]):
            families.append("mean_reversion_family")
        if any(k in text for k in ["momentum", "trend"]):
            families.append("momentum_family")
        if any(k in text for k in ["cross-sectional", "stat-arb", "sector-neutral", "residual"]):
            families.append("stat_arb_family")
        if not families:
            families.append("stat_arb_family")

        primitives = []
        if any(k in text for k in ["volume", "liquidity", "order-flow"]):
            primitives.append("volume_divergence_signal")
        if "vwap" in text:
            primitives.append("vwap_anchor_signal")
        if "hurst" in text:
            primitives.append("hurst_filter_signal")

        data_sources = ["price_volume_data_source"]
        if any(k in text for k in ["inflation", "fed", "macro", "yield", "trade", "ppi"]):
            data_sources.append("macro_data_source")
        if any(k in text for k in ["sector", "industry", "cross-sectional"]):
            data_sources.append("sector_data_source")

        regimes = []
        if any(k in text for k in ["high-vol", "high volatility", "bearish", "bear regime"]):
            regimes.append("high_volatility_regime")
        if any(k in text for k in ["pivot", "fed", "policy"]):
            regimes.append("policy_pivot_regime")
        if not regimes:
            regimes.append("market_regime_base")

        risk_flags = []
        if str(meta.get("simulated", "")).lower() in {"true", "1", "yes"} or "simulated" in text:
            risk_flags.append("simulation_only_risk")
        if "deviates from hypothesis" in text or "mismatch" in text or "implementation drift" in text:
            risk_flags.append("implementation_drift_risk")
        if "turnover" in text or "cost" in text:
            risk_flags.append("turnover_explosion_risk")

        metrics_ref = ["information_coefficient_metric", "rank_ic_metric"]
        if any(k in text for k in ["sharpe", "drawdown", "turnover", "cost drag"]):
            metrics_ref.append("strategy_risk_metrics_reference")

        execution_patterns = []
        impl = sections.get("Implementation (Qlib)", "").lower()
        if "rank(" in impl or "csrank" in impl:
            execution_patterns.append("cross_sectional_long_short_execution")
        if "threshold" in text:
            execution_patterns.append("threshold_timing_execution")
        if "long-only" in text or "long only" in text:
            execution_patterns.append("long_only_selection_execution")
        if not execution_patterns:
            execution_patterns.append("cross_sectional_long_short_execution")

        evidence_level = meta.get("evidence_level")
        if not evidence_level:
            if str(meta.get("simulated", "")).lower() in {"true", "1", "yes"}:
                evidence_level = "simulated"
            elif str(meta.get("is_effective", "")).lower() in {"true", "1", "yes"}:
                evidence_level = "validated"
            else:
                evidence_level = "theory"

        status = meta.get("status", "candidate")
        if status == "proven":
            status = "active"
        elif status in {"failed", "deprecated", "baseline"}:
            status = {"failed": "failed", "deprecated": "deprecated", "baseline": "active"}[status]
        elif status == "draft":
            status = "candidate"

        return {
            "type": "experiment_card",
            "node_type": meta.get("node_type", "factor_experiment"),
            "evidence_level": evidence_level,
            "status": status,
            "canonical": False,
            "parents": list(dict.fromkeys(families)),
            "depends_on": list(dict.fromkeys(primitives + data_sources + regimes + execution_patterns)),
            "risk_flags": list(dict.fromkeys(risk_flags)),
            "metrics_ref": list(dict.fromkeys(metrics_ref)),
            "strategy_family": list(dict.fromkeys(families)),
            "data_sources": list(dict.fromkeys(data_sources)),
            "market_regimes": list(dict.fromkeys(regimes)),
            "execution_patterns": list(dict.fromkeys(execution_patterns)),
            "related_experiments": [],
            "related": list(
                dict.fromkeys(
                    (meta.get("related") or [])
                    + families
                    + primitives
                    + data_sources
                    + regimes
                    + risk_flags
                    + metrics_ref
                    + execution_patterns
                )
            ),
        }

    def _render_experiment_card(self, title: str, meta: Dict[str, Any], sections: Dict[str, str]) -> str:
        summary = meta.get("summary") or sections.get("Hypothesis") or title
        implementation = sections.get("Implementation (Qlib)") or "N/A"
        metrics_line = sections.get("IC / RankIC") or (
            f"{float(meta.get('ic') or 0.0):.4f} / {float(meta.get('rank_ic') or 0.0):.4f}"
        )
        related_concepts = []
        for key in ("strategy_family", "data_sources", "market_regimes", "execution_patterns"):
            for slug in meta.get(key, []) or []:
                related_concepts.append(f"- [[{slug}]]")
        if not related_concepts:
            related_concepts.append("- [[strategy_families_base]]")

        risk_lines = [f"- [[{slug}]]" for slug in meta.get("risk_flags", [])] or ["- None recorded"]
        next_steps = sections.get("Suggested Improvements") or "Promote or refine after collecting stronger evidence."

        return "\n".join(
            [
                f"# {title}",
                "",
                "## Summary",
                "",
                summary,
                "",
                "## Hypothesis",
                "",
                sections.get("Hypothesis") or summary,
                "",
                "## Economic Rationale",
                "",
                sections.get("Rationale") or "Rationale not yet captured.",
                "",
                "## Formula / Implementation",
                "",
                f"**Implementation (Qlib)**: `{implementation}`",
                "",
                sections.get("Math Formula") and f"**Math Formula**: {sections.get('Math Formula')}" or "",
                "",
                "## Backtest Evidence",
                "",
                f"- **Evidence Level:** `{meta.get('evidence_level', 'theory')}`",
                f"- **Status:** `{meta.get('status', 'candidate')}`",
                f"- **IC / RankIC:** {metrics_line}",
                f"- **Effectiveness:** {sections.get('Effectiveness') or ('✅ effective' if meta.get('is_effective') else '❌ not validated')}",
                "",
                "## Interpretation",
                "",
                sections.get("Review Summary") or "Interpretation pending.",
                "",
                "## Failure Modes / Risks",
                "",
                *risk_lines,
                "",
                "## Related Concepts",
                "",
                *related_concepts,
                "",
                "## Next Steps",
                "",
                next_steps,
            ]
        ).replace("\n\n\n", "\n\n").strip() + "\n"

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
        try:
            self.wiki_col.upsert(
                ids=[page_id],
                documents=[f"# {title}\n\n{full_meta['summary']}\n\n{content}"],
                metadatas=[chroma_meta],
            )
        except Exception as e:
            logger.warning(
                f"[Wiki] Embedding upsert failed for '{slug}'; filesystem write succeeded but vector index is stale: {e}"
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
        pages = self._scan_pages()
        entries: List[Dict[str, Any]] = []
        for slug, page in pages.items():
            meta = page["meta"]
            entries.append(
                {
                    "slug": slug,
                    "title": meta.get("title") or slug.replace("_", " "),
                    "type": meta.get("type") or "uncategorized",
                    "status": meta.get("status") or "",
                    "summary": meta.get("summary") or "",
                    "updated": meta.get("updated") or "",
                    "evidence_level": meta.get("evidence_level") or "",
                }
            )

        by_type: Dict[str, List[Dict[str, Any]]] = {}
        by_evidence: Dict[str, List[Dict[str, Any]]] = {}
        for e in entries:
            by_type.setdefault(e["type"], []).append(e)
            by_evidence.setdefault(e["evidence_level"] or "unspecified", []).append(e)
        for group in list(by_type.values()) + list(by_evidence.values()):
            group.sort(key=lambda x: x.get("updated") or "", reverse=True)

        type_order = [
            "strategy_family",
            "signal_primitive",
            "market_regime",
            "data_source",
            "risk_pattern",
            "evaluation_metric",
            "execution_pattern",
            "experiment_card",
        ]
        evidence_order = ["baseline", "theory", "simulated", "validated", "production", "unspecified"]

        lines: List[str] = []
        lines.append("# Wiki Index (Compiled)\n")
        lines.append(
            f"*Last compiled: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} · "
            f"{len(entries)} pages across {len(by_type)} node categories*\n"
        )
        lines.append("\n## Browse by Concept\n")
        for t in [t for t in type_order if t in by_type]:
            lines.append(f"- [[{TAXONOMY_SLUGS[t]}]] {t.replace('_', ' ').title()} ({len(by_type[t])})")

        lines.append("\n## Browse by Evidence Level\n")
        for ev in [e for e in evidence_order if e in by_evidence]:
            lines.append(f"- `{ev}` ({len(by_evidence[ev])})")
            for item in by_evidence[ev][:8]:
                lines.append(f"  - [[{item['slug']}]] **{item['title']}**")

        lines.append("\n## Browse by Experiments\n")
        for item in by_type.get("experiment_card", [])[:40]:
            lines.append(
                f"- [[{item['slug']}]] **{item['title']}** · `{item['evidence_level'] or 'unspecified'}` — {item['summary']}"
            )

        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self._recompile_taxonomy_pages(pages)

    def _recompile_taxonomy_pages(self, pages: Dict[str, Dict[str, Any]]):
        taxonomy_specs = [
            ("graph_overview", "Graph Overview", "How the research wiki is organized into concept, evidence, and experiment layers."),
            ("evidence_levels", "Evidence Levels", "How baseline, theory, simulated, validated, and production evidence should be interpreted."),
        ]
        for slug, title, summary in taxonomy_specs:
            path = os.path.join(self.wiki_vault, f"{slug}.md")
            content = (
                "# " + title + "\n\n"
                "## Role\n\n"
                + summary
                + "\n\n## Node Types\n\n- strategy_family\n- signal_primitive\n- market_regime\n- data_source\n- risk_pattern\n- evaluation_metric\n- execution_pattern\n- experiment_card\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    _dump_frontmatter(
                        {
                            "title": title,
                            "slug": slug,
                            "type": "taxonomy",
                            "status": "active",
                            "summary": summary,
                            "updated": datetime.utcnow().isoformat(timespec="seconds"),
                            "evidence_level": "baseline",
                            "canonical": True,
                        }
                    )
                )
                f.write(content)

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for slug, page in pages.items():
            meta = page["meta"]
            if (meta.get("type") or "uncategorized") == "taxonomy":
                continue
            grouped.setdefault(meta.get("type") or "uncategorized", []).append(
                {
                    "slug": slug,
                    "title": meta.get("title", slug),
                    "summary": meta.get("summary", ""),
                    "evidence_level": meta.get("evidence_level", ""),
                    "status": meta.get("status", ""),
                }
            )

        for node_type, items in grouped.items():
            items.sort(key=lambda x: x["title"])
            slug = TAXONOMY_SLUGS.get(node_type, f"taxonomy_{node_type}s")
            title = f"Taxonomy: {node_type.replace('_', ' ').title()}"
            body_lines = [
                f"# {title}",
                "",
                "## Purpose",
                "",
                f"This page groups all `{node_type}` nodes and highlights how they relate to the research graph.",
                "",
                "## Nodes",
                "",
            ]
            for item in items:
                body_lines.append(
                    f"- [[{item['slug']}]] **{item['title']}** · `{item['evidence_level'] or 'unspecified'}` / `{item['status'] or 'n/a'}` — {item['summary']}"
                )
            with open(os.path.join(self.wiki_vault, f"{slug}.md"), "w", encoding="utf-8") as f:
                f.write(
                    _dump_frontmatter(
                        {
                            "title": title,
                            "slug": slug,
                            "type": "taxonomy",
                            "status": "active",
                            "summary": f"Taxonomy page for {node_type}.",
                            "updated": datetime.utcnow().isoformat(timespec="seconds"),
                            "evidence_level": "baseline",
                            "canonical": True,
                        }
                    )
                )
                f.write("\n".join(body_lines) + "\n")

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

            page_type = self._canonical_type(meta.get("type") or "experiment_card")
            title = meta.get("title") or slug.replace("_", " ").title()

            # Infer status
            status = meta.get("status")
            if not status:
                if page_type in {"market_regime", "signal_primitive", "strategy_family"}:
                    status = "baseline"
                elif "✅ EFFECTIVE" in body or "Effectiveness: ✅" in body:
                    status = "proven"
                elif "❌ FAILED" in body or "Effectiveness: ❌" in body:
                    status = "failed"
                else:
                    status = "draft"

            # Derive summary if missing
            summary = meta.get("summary") or self._derive_summary(body)

            # Default related: experiment cards link back to the strategy family
            # baseline so they are not lint-flagged as orphans.
            related = meta.get("related")
            if not related:
                related = ["strategy_families_base"] if page_type == "experiment_card" else []

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

    def upgrade_to_graph_schema(self, dry_run: bool = False) -> Dict[str, Any]:
        self._ensure_graph_pages()
        pages = self._scan_pages()
        upgraded: List[str] = []
        skipped: List[str] = []
        for slug, page in pages.items():
            if slug in {"index", "log"} or slug.startswith("taxonomy_") or slug in {"graph_overview", "evidence_levels"}:
                skipped.append(slug)
                continue
            meta = page["meta"].copy()
            body = page["body"]
            page_type = self._canonical_type(meta.get("type", "experiment_card"))
            title = meta.get("title") or slug.replace("_", " ").title()

            if page_type in GRAPH_NODE_TYPES - {"experiment_card"}:
                meta["type"] = page_type
                meta.setdefault("node_type", page_type)
                meta.setdefault("evidence_level", "baseline")
                meta.setdefault("status", "active")
                meta.setdefault("canonical", True)
                meta.setdefault("parents", [])
                meta.setdefault("depends_on", [])
                meta.setdefault("risk_flags", [])
                meta.setdefault("metrics_ref", [])
                new_body = body.strip() + ("\n" if body.strip() else "")
            else:
                sections = self._extract_experiment_sections(body)
                inferred = self._infer_graph_metadata(slug, meta, body, sections)
                meta.update(inferred)
                meta["title"] = title
                meta["slug"] = slug
                meta["summary"] = meta.get("summary") or self._derive_summary(body)
                meta["updated"] = meta.get("updated") or datetime.utcnow().isoformat(timespec="seconds")
                new_body = self._render_experiment_card(title, meta, sections)

            if dry_run:
                upgraded.append(slug)
                continue
            with open(page["path"], "w", encoding="utf-8") as f:
                f.write(_dump_frontmatter(meta))
                f.write(new_body)
            upgraded.append(slug)

        if not dry_run:
            refreshed = self._scan_pages()
            for slug, page in refreshed.items():
                related = page["meta"].get("related") or []
                self._backlink_audit(slug, page["meta"].get("title", slug), related)
            self._recompile_index()
            self._log_event("GRAPH_UPGRADE", "wiki_graph", "Wiki Graph Upgrade", extra=f"{len(upgraded)} pages")

        return {"upgraded": upgraded, "skipped": skipped, "dry_run": dry_run}

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

            page_type = self._canonical_type(str(meta.get("type", "")))

            # ERROR: experiment card marked as validated but is_effective=false
            status = str(meta.get("status", "")).lower()
            evidence_level = str(meta.get("evidence_level", "")).lower()
            ie_raw = str(meta.get("is_effective", "")).lower()
            if page_type == "experiment_card":
                if evidence_level in {"validated", "production"} and ie_raw in {"false", "0", "no"}:
                    errors.append(
                        f"`{slug}` has evidence_level={evidence_level} but is_effective=false — contradiction."
                    )
                if status == "failed" and ie_raw in {"true", "1", "yes"}:
                    errors.append(
                        f"`{slug}` has status=failed but is_effective=true — contradiction."
                    )

            if page_type not in GRAPH_NODE_TYPES and page_type != "taxonomy":
                warnings.append(f"`{slug}` has non-graph type `{page_type}`.")

            if evidence_level and evidence_level not in EVIDENCE_LEVELS:
                warnings.append(f"`{slug}` has unknown evidence_level `{evidence_level}`.")

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

            # WARNING: experiment card with no parent strategy family
            if page_type == "experiment_card":
                related = set(meta.get("related") or [])
                related.update(meta.get("parents") or [])
                has_family = any(
                    self._canonical_type(pages.get(r, {}).get("meta", {}).get("type", "")) == "strategy_family"
                    for r in related
                )
                if not has_family:
                    warnings.append(
                        f"`{slug}` is an experiment_card with no parent strategy_family in `related`/`parents`."
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
