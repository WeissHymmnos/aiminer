import glob
import hashlib
import json
import os
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv
from loguru import logger

from core.llm import get_llm_config

load_dotenv()

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


class RAGModule:
    RECENT_ENTRY_LIMIT = 120
    RECENT_QUERY_RESULTS = 3
    SUMMARY_QUERY_RESULTS = 2
    ARCHIVE_QUERY_RESULTS = 1
    SUMMARY_MIN_GROUP_SIZE = 2
    EXPERIENCE_BATCH_SIZE = 16

    def __init__(
        self,
        db_dir: str = "data/chroma_db",
        docs_dir: str = "data/rag_docs",
        rebuild: bool = False,
        embedding_provider: str = None,
        use_gpu: bool = False,
    ):
        self.retrieval_enabled = True
        self.memory_enabled = True
        self.disabled_reason = ""
        self.docs_dir = docs_dir
        self.rebuild = rebuild
        os.makedirs(self.docs_dir, exist_ok=True)
        self.embedding_fn = None
        self.client = None
        self.knowledge_col = None
        self.legacy_experiences_col = None
        self.experiences_recent_col = None
        self.experiences_summary_col = None
        self.experiences_archive_col = None

        use_local = (embedding_provider == "local") or (os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true")

        model_tag = "api"
        try:
            if use_local:
                model_name = "Qwen/Qwen3-Embedding-4B"
                model_tag = model_name.replace("/", "_")
                device = "cuda" if use_gpu else "cpu"
                logger.info(f"Initializing LARGE LOCAL embedding model ({model_name}) on {device}...")
                try:
                    self.embedding_fn = SentenceTransformerEmbeddingFunction(
                        model_name=model_name,
                        device=device,
                        trust_remote_code=True,
                    )
                except Exception as e:
                    logger.warning(f"Note: Hub connection sluggish ({e}). Trying mirror fallback...")
                    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                    self.embedding_fn = SentenceTransformerEmbeddingFunction(
                        model_name=model_name,
                        device=device,
                        trust_remote_code=True,
                    )
            else:
                embedding_defaults = {
                    "kimi": {"model_name": "embedding-2", "api_base": "https://api.moonshot.cn/v1"},
                    "qwen": {"model_name": "text-embedding-v3", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
                    "claude": {"model_name": "text-embedding-3-small", "api_base": "https://api.gptsapi.net/v1"},
                    "glm": {"model_name": "embedding-3", "api_base": "https://open.bigmodel.cn/api/paas/v4"},
                }

                try:
                    cfg = get_llm_config(provider=embedding_provider)
                    provider = cfg["provider"]
                    model_tag = provider
                    api_key = cfg["api_key"]
                    emb_defaults = embedding_defaults[provider]

                    logger.info(f"Initializing API-based embedding ({provider})...")
                    self.embedding_fn = OpenAIEmbeddingFunction(
                        api_key=api_key,
                        model_name=emb_defaults["model_name"],
                        api_base=emb_defaults["api_base"],
                    )
                except (ValueError, KeyError):
                    logger.warning("No API key or provider found for embeddings. Falling back to LOCAL bge-large.")
                    model_tag = "bge-large"
                    self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-zh-v1.5")

            self.db_dir = os.path.join(db_dir, model_tag)
            os.makedirs(self.db_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.db_dir)

            self.experience_log_path = os.path.join(self.db_dir, "experience_memory.jsonl")
            self.experience_lock_path = os.path.join(self.db_dir, "experience_memory.lock")
            self.legacy_idea_log_path = os.path.join(os.path.dirname(self.db_dir), "idea_experiences.jsonl")

            self.knowledge_col = self._get_or_create_collection("knowledge_base")
            self.legacy_experiences_col = self._get_or_create_collection("experiences")
            self.experiences_recent_col = self._get_or_create_collection("experiences_recent")
            self.experiences_summary_col = self._get_or_create_collection("experiences_summary")
            self.experiences_archive_col = self._get_or_create_collection("experiences_archive")

            try:
                self._init_knowledge_base()
                self._init_experience_memory()
            except Exception as e:
                self.retrieval_enabled = False
                self.memory_enabled = False
                self.disabled_reason = f"RAG disabled after initialization failure: {e}"
                logger.warning(self.disabled_reason)
        except Exception as e:
            self.retrieval_enabled = False
            self.memory_enabled = False
            self.disabled_reason = f"RAG disabled: {e}"
            self.db_dir = os.path.join(db_dir, "disabled")
            self.experience_log_path = os.path.join(self.db_dir, "experience_memory.jsonl")
            self.experience_lock_path = os.path.join(self.db_dir, "experience_memory.lock")
            self.legacy_idea_log_path = os.path.join(db_dir, "idea_experiences.jsonl")
            logger.warning(self.disabled_reason)

    def _get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name, embedding_function=self.embedding_fn)

    def _recreate_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        return self._get_or_create_collection(name)

    @contextmanager
    def _experience_lock(self):
        os.makedirs(os.path.dirname(self.experience_lock_path), exist_ok=True)
        with open(self.experience_lock_path, "a+b") as lock_file:
            if os.name == "nt":
                import msvcrt

                if lock_file.tell() == 0:
                    lock_file.write(b"0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) < chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(paragraph) > chunk_size:
                    chunks.append(paragraph)
                    current_chunk = ""
                else:
                    current_chunk = paragraph + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _init_knowledge_base(self):
        if self.rebuild and self.knowledge_col.count() > 0:
            logger.info("Rebuilding knowledge base: deleting existing documents...")
            self.knowledge_col = self._recreate_collection("knowledge_base")

        if self.knowledge_col.count() > 0:
            logger.info(f"Knowledge base already initialized with {self.knowledge_col.count()} documents.")
            return

        logger.info(f"Scanning {self.docs_dir} for knowledge base documents...")

        doc_files: List[str] = []
        for ext in ("*.md", "*.rst", "*.txt"):
            doc_files.extend(glob.glob(os.path.join(self.docs_dir, "**", ext), recursive=True))

        if not doc_files:
            logger.warning(f"No documents found in {self.docs_dir}.")
            return

        all_chunks: List[str] = []
        all_metadatas: List[Dict[str, Any]] = []
        all_ids: List[str] = []
        doc_id_counter = 0

        for file_path in doc_files:
            try:
                with open(file_path, "r", encoding="utf-8") as file_obj:
                    content = file_obj.read()

                for chunk_index, chunk in enumerate(self._chunk_text(content)):
                    if not chunk.strip():
                        continue
                    all_chunks.append(chunk)
                    all_metadatas.append({"source": file_path, "chunk": chunk_index})
                    all_ids.append(f"doc_{doc_id_counter}")
                    doc_id_counter += 1
            except Exception as e:
                logger.error(f"Failed to read/process {file_path}: {e}")

        if not all_chunks:
            return

        logger.info(f"Loading {len(all_chunks)} chunks into knowledge base...")
        try:
            batch_size = 8
            for index in range(0, len(all_chunks), batch_size):
                self.knowledge_col.add(
                    documents=all_chunks[index:index + batch_size],
                    metadatas=all_metadatas[index:index + batch_size],
                    ids=all_ids[index:index + batch_size],
                )
            logger.info("Knowledge base successfully populated.")
        except Exception as e:
            logger.error(f"Failed to populate knowledge base: {e}")

    def _safe_query(self, collection, query: str, n_results: int):
        if not self.retrieval_enabled or collection is None:
            return None
        count = collection.count()
        if count == 0:
            return None
        return collection.query(query_texts=[query], n_results=min(n_results, count))

    @staticmethod
    def _json_default(value: Any):
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _slugify(value: str) -> str:
        lowered = (value or "unknown").lower()
        cleaned = []
        prev_sep = False
        for ch in lowered:
            if ch.isalnum():
                cleaned.append(ch)
                prev_sep = False
            elif not prev_sep:
                cleaned.append("_")
                prev_sep = True
        return "".join(cleaned).strip("_") or "unknown"

    @staticmethod
    def _first_non_empty(*values: Optional[str]) -> str:
        for value in values:
            if value and str(value).strip():
                return str(value).strip()
        return ""

    def _extract_field_from_document(self, document: str, field_name: str) -> str:
        prefix = f"{field_name}:"
        for line in (document or "").splitlines():
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        return ""

    def _init_experience_memory(self):
        with self._experience_lock():
            self._migrate_legacy_experiences_if_needed()
            self._refresh_experience_layers_locked()

    def _migrate_legacy_experiences_if_needed(self):
        if os.path.exists(self.experience_log_path) and os.path.getsize(self.experience_log_path) > 0:
            return

        migrated_entries: List[Dict[str, Any]] = []

        if self.legacy_experiences_col.count() > 0:
            try:
                legacy = self.legacy_experiences_col.get(include=["documents", "metadatas"])
                ids = legacy.get("ids", [])
                documents = legacy.get("documents", [])
                metadatas = legacy.get("metadatas", [])
                for index, document in enumerate(documents):
                    metadata = metadatas[index] if index < len(metadatas) else {}
                    legacy_id = ids[index] if index < len(ids) else f"legacy_{index}"
                    entry = self._normalize_experience_entry(
                        {
                            "entry_id": f"legacy_{legacy_id}",
                            "timestamp": metadata.get("timestamp"),
                            "hypothesis_name": self._extract_field_from_document(document, "Hypothesis"),
                            "hypothesis": self._extract_field_from_document(document, "Hypothesis"),
                            "code": self._extract_field_from_document(document, "Code"),
                            "metrics": {
                                "information_coefficient": metadata.get("ic", 0.0),
                                "rank_ic": metadata.get("rank_ic", 0.0),
                            },
                            "is_effective": bool(metadata.get("is_effective", False)),
                            "review": self._extract_field_from_document(document, "Review"),
                            "evaluation_mode": metadata.get("evaluation_mode", "legacy"),
                            "source": "legacy_chroma",
                        }
                    )
                    migrated_entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to migrate legacy Chroma experiences: {e}")

        if os.path.exists(self.legacy_idea_log_path):
            try:
                with open(self.legacy_idea_log_path, "r", encoding="utf-8") as file_obj:
                    for line in file_obj:
                        line = line.strip()
                        if not line:
                            continue
                        raw = json.loads(line)
                        if "hypothesis" not in raw and "metrics" not in raw:
                            continue
                        entry = self._normalize_experience_entry(
                            {
                                "entry_id": f"legacy_file_{uuid.uuid4().hex}",
                                "timestamp": raw.get("timestamp"),
                                "hypothesis_name": raw.get("idea_name") or raw.get("hypothesis"),
                                "hypothesis": raw.get("hypothesis") or raw.get("description") or raw.get("document"),
                                "code": raw.get("code", ""),
                                "metrics": raw.get("metrics", {}),
                                "is_effective": raw.get("is_effective", False),
                                "review": raw.get("review", ""),
                                "suggested_improvements": "; ".join(raw.get("failure_modes", [])),
                                "source": "legacy_jsonl",
                            }
                        )
                        migrated_entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to migrate legacy JSONL experiences: {e}")

        if not migrated_entries:
            return

        deduped: Dict[str, Dict[str, Any]] = {}
        for entry in migrated_entries:
            fingerprint = self._experience_fingerprint(entry)
            deduped[fingerprint] = entry

        with open(self.experience_log_path, "w", encoding="utf-8") as file_obj:
            for entry in sorted(deduped.values(), key=lambda item: self._parse_timestamp(item["timestamp"])):
                file_obj.write(json.dumps(entry, ensure_ascii=False, default=self._json_default) + "\n")

        logger.info(f"Migrated {len(deduped)} legacy experience records into layered memory ledger.")

    def _experience_fingerprint(self, entry: Dict[str, Any]) -> str:
        payload = {
            "hypothesis": entry.get("hypothesis", ""),
            "code": entry.get("code", ""),
            "review": entry.get("review", ""),
            "timestamp": entry.get("timestamp", ""),
        }
        return hashlib.md5(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _normalize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for key, value in (metrics or {}).items():
            if value is None:
                continue
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                continue
        return normalized

    def _infer_market_regime_tag(self, market_regime: str) -> str:
        text = (market_regime or "").lower()
        tags = []
        if "bearish" in text or "below ma20" in text:
            tags.append("bearish")
        elif "bullish" in text or "above ma20" in text:
            tags.append("bullish")

        if "high volatility" in text:
            tags.append("high_vol")
        elif "low volatility" in text:
            tags.append("low_vol")
        elif "normal volatility" in text:
            tags.append("normal_vol")

        if "shrinking" in text:
            tags.append("shrinking_volume")
        elif "expanding" in text:
            tags.append("expanding_volume")

        return "+".join(tags) if tags else "unknown_regime"

    def _infer_factor_family(self, hypothesis: str, code: str, review: str) -> str:
        text = " ".join(filter(None, [hypothesis, code, review])).lower()
        families = {
            "vwap_liquidity": ["vwap", "volume", "liquidity", "turnover"],
            "reversal": ["reversal", "mean reversion", "exhaustion", "fade"],
            "momentum": ["momentum", "trend", "breakout", "macd"],
            "volatility_range": ["volatility", "dispersion", "range", "high", "low"],
            "correlation_structure": ["corr", "correlation", "cov", "relationship"],
            "price_location": ["close", "open", "price", "midpoint"],
        }
        scores = {family: sum(keyword in text for keyword in keywords) for family, keywords in families.items()}
        best_family, best_score = max(scores.items(), key=lambda item: item[1])
        return best_family if best_score > 0 else "general_alpha"

    def _infer_failure_type(self, metrics: Dict[str, float], is_effective: bool, review: str, is_simulated: bool) -> str:
        if is_effective:
            return "effective"
        if is_simulated:
            return "simulated_eval"

        ic = metrics.get("information_coefficient", 0.0)
        rank_ic = metrics.get("rank_ic", 0.0)
        diversity = metrics.get("diversity", 1.0)
        text = (review or "").lower()

        if ic < 0 and rank_ic < 0:
            return "sign_reversed"
        if abs(ic) < 0.02 and abs(rank_ic) < 0.02:
            return "weak_predictive_power"
        if diversity < 0.15 or "concentrated" in text:
            return "low_diversity"
        if "syntax" in text or "invalid" in text:
            return "implementation_issue"
        return "ineffective"

    def _normalize_experience_entry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = raw.get("timestamp") or datetime.now(timezone.utc).isoformat()
        metrics = self._normalize_metrics(raw.get("metrics", {}))
        is_effective = bool(raw.get("is_effective", False))
        is_simulated = bool(raw.get("is_simulated", False))
        hypothesis = self._first_non_empty(raw.get("hypothesis"), raw.get("hypothesis_description"), raw.get("document"))
        review = self._first_non_empty(raw.get("review"), raw.get("review_summary"))
        market_regime = raw.get("market_regime", "") or ""
        factor_family = self._first_non_empty(
            raw.get("factor_family"),
            self._infer_factor_family(hypothesis, raw.get("code", ""), review),
        )
        failure_type = self._first_non_empty(
            raw.get("failure_type"),
            self._infer_failure_type(metrics, is_effective, review, is_simulated),
        )

        return {
            "entry_id": raw.get("entry_id") or f"exp_{uuid.uuid4().hex}",
            "timestamp": timestamp,
            "iteration": int(raw.get("iteration", 0) or 0),
            "hypothesis_name": self._first_non_empty(raw.get("hypothesis_name"), hypothesis[:120]),
            "hypothesis": hypothesis,
            "code": raw.get("code", "") or "",
            "metrics": metrics,
            "is_effective": is_effective,
            "is_simulated": is_simulated,
            "review": review,
            "suggested_improvements": self._first_non_empty(raw.get("suggested_improvements")),
            "evaluation_mode": self._first_non_empty(raw.get("evaluation_mode"), "unknown"),
            "market_regime": market_regime,
            "market_regime_tag": self._first_non_empty(raw.get("market_regime_tag"), self._infer_market_regime_tag(market_regime)),
            "factor_family": factor_family,
            "failure_type": failure_type,
            "role_prompt": self._first_non_empty(raw.get("role_prompt")),
            "source": self._first_non_empty(raw.get("source"), "live_eval"),
        }

    def _load_experience_entries_locked(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.experience_log_path):
            return []

        entries: List[Dict[str, Any]] = []
        with open(self.experience_log_path, "r", encoding="utf-8") as file_obj:
            for line in file_obj:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(self._normalize_experience_entry(json.loads(line)))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed experience log line: {e}")

        entries.sort(key=lambda item: self._parse_timestamp(item["timestamp"]))
        return entries

    def _append_experience_entry_locked(self, entry: Dict[str, Any]):
        os.makedirs(os.path.dirname(self.experience_log_path), exist_ok=True)
        with open(self.experience_log_path, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(entry, ensure_ascii=False, default=self._json_default) + "\n")

    def _build_experience_document(self, entry: Dict[str, Any]) -> str:
        metrics_json = json.dumps(entry["metrics"], ensure_ascii=False, sort_keys=True)
        return (
            f"Timestamp: {entry['timestamp']}\n"
            f"Iteration: {entry['iteration']}\n"
            f"Status: {'effective' if entry['is_effective'] else 'ineffective'}\n"
            f"Simulation: {entry['is_simulated']}\n"
            f"Evaluation Mode: {entry['evaluation_mode']}\n"
            f"Factor Family: {entry['factor_family']}\n"
            f"Failure Type: {entry['failure_type']}\n"
            f"Market Regime: {entry['market_regime_tag']}\n"
            f"Hypothesis: {entry['hypothesis']}\n"
            f"Code: {entry['code']}\n"
            f"Metrics: {metrics_json}\n"
            f"Review: {entry['review']}\n"
            f"Suggested Improvements: {entry['suggested_improvements'] or 'N/A'}"
        )

    def _build_summary_payloads(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in entries:
            key = f"{entry['factor_family']}|{entry['failure_type']}|{entry['market_regime_tag']}"
            grouped[key].append(entry)

        payloads: List[Dict[str, Any]] = []
        for group_key, group_entries in grouped.items():
            if len(group_entries) < self.SUMMARY_MIN_GROUP_SIZE:
                continue

            group_entries.sort(key=lambda item: self._parse_timestamp(item["timestamp"]), reverse=True)
            factor_family, failure_type, regime_tag = group_key.split("|", 2)
            effective_count = sum(1 for entry in group_entries if entry["is_effective"])
            avg_ic = sum(entry["metrics"].get("information_coefficient", 0.0) for entry in group_entries) / len(group_entries)
            avg_rank_ic = sum(entry["metrics"].get("rank_ic", 0.0) for entry in group_entries) / len(group_entries)
            representative = [entry["hypothesis_name"] for entry in group_entries[:3] if entry["hypothesis_name"]]
            improvements = []
            for entry in group_entries:
                improvement = entry.get("suggested_improvements")
                if improvement and improvement not in improvements:
                    improvements.append(improvement)
                if len(improvements) >= 3:
                    break

            summary_doc = (
                f"Memory Summary Group: {factor_family} / {failure_type} / {regime_tag}\n"
                f"Entries: {len(group_entries)}\n"
                f"Effective Count: {effective_count}\n"
                f"Average IC: {avg_ic:.4f}\n"
                f"Average Rank IC: {avg_rank_ic:.4f}\n"
                f"Representative Hypotheses: {'; '.join(representative) or 'N/A'}\n"
                f"Typical Improvements: {'; '.join(improvements) or 'N/A'}\n"
                f"Latest Review Signal: {group_entries[0]['review'][:400]}"
            )

            payloads.append(
                {
                    "id": f"summary_{self._slugify(group_key)}",
                    "document": summary_doc,
                    "metadata": {
                        "layer": "summary",
                        "group_key": group_key,
                        "factor_family": factor_family,
                        "failure_type": failure_type,
                        "market_regime_tag": regime_tag,
                        "entry_count": len(group_entries),
                        "effective_count": effective_count,
                        "avg_ic": avg_ic,
                        "avg_rank_ic": avg_rank_ic,
                        "latest_timestamp": group_entries[0]["timestamp"],
                    },
                }
            )

        return payloads

    def _payloads_from_entries(self, entries: List[Dict[str, Any]], layer: str) -> List[Dict[str, Any]]:
        payloads = []
        for entry in entries:
            payloads.append(
                {
                    "id": entry["entry_id"],
                    "document": self._build_experience_document(entry),
                    "metadata": {
                        "layer": layer,
                        "timestamp": entry["timestamp"],
                        "iteration": entry["iteration"],
                        "is_effective": entry["is_effective"],
                        "is_simulated": entry["is_simulated"],
                        "factor_family": entry["factor_family"],
                        "failure_type": entry["failure_type"],
                        "market_regime_tag": entry["market_regime_tag"],
                        "evaluation_mode": entry["evaluation_mode"],
                        "ic": entry["metrics"].get("information_coefficient", 0.0),
                        "rank_ic": entry["metrics"].get("rank_ic", 0.0),
                    },
                }
            )
        return payloads

    def _bulk_load_collection(self, name: str, payloads: List[Dict[str, Any]]):
        collection = self._recreate_collection(name)
        if not payloads:
            return collection

        for index in range(0, len(payloads), self.EXPERIENCE_BATCH_SIZE):
            batch = payloads[index:index + self.EXPERIENCE_BATCH_SIZE]
            collection.add(
                ids=[item["id"] for item in batch],
                documents=[item["document"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
            )
        return collection

    def _refresh_experience_layers_locked(self):
        entries = self._load_experience_entries_locked()
        recent_entries = list(reversed(entries[-self.RECENT_ENTRY_LIMIT:]))
        archive_entries = list(reversed(entries))

        self.experiences_recent_col = self._bulk_load_collection(
            "experiences_recent",
            self._payloads_from_entries(recent_entries, layer="recent"),
        )
        self.experiences_archive_col = self._bulk_load_collection(
            "experiences_archive",
            self._payloads_from_entries(archive_entries, layer="archive"),
        )
        self.experiences_summary_col = self._bulk_load_collection(
            "experiences_summary",
            self._build_summary_payloads(entries),
        )

    def _format_result_block(self, title: str, results) -> List[str]:
        lines = [title] if title else []
        if results and results.get("documents") and results["documents"][0]:
            for document in results["documents"][0]:
                lines.append(f"- {document}")
        else:
            lines.append("No relevant entries found.")
        return lines

    def retrieve(self, query: str, n_results: int = 2, include_experiences: bool = True) -> str:
        if not self.retrieval_enabled:
            return f"=== KNOWLEDGE BASE ===\n(RAG disabled: {self.disabled_reason or 'embedding unavailable'})"
        try:
            knowledge_results = self._safe_query(self.knowledge_col, query, n_results)
            context_parts = self._format_result_block("=== KNOWLEDGE BASE ===", knowledge_results)

            if include_experiences:
                recent_results = self._safe_query(
                    self.experiences_recent_col,
                    query,
                    max(self.RECENT_QUERY_RESULTS, n_results),
                )
                summary_results = self._safe_query(
                    self.experiences_summary_col,
                    query,
                    max(self.SUMMARY_QUERY_RESULTS, max(1, n_results - 1)),
                )
                archive_results = self._safe_query(
                    self.experiences_archive_col,
                    query,
                    max(self.ARCHIVE_QUERY_RESULTS, 1),
                )

                context_parts.extend(["", "=== RECENT EXPERIENCES ==="])
                context_parts.extend(self._format_result_block("", recent_results))
                context_parts.extend(["", "=== EXPERIENCE SUMMARIES ==="])
                context_parts.extend(self._format_result_block("", summary_results))
                context_parts.extend(["", "=== ARCHIVED EXPERIENCES ==="])
                context_parts.extend(self._format_result_block("", archive_results))
            else:
                return "\n".join(context_parts)

            return "\n".join(context_parts)

        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg or "not open" in err_msg.lower():
                logger.warning("RAG Embedding API is not enabled for this provider. Running without vector retrieval context.")
                if include_experiences:
                    return (
                        "=== KNOWLEDGE BASE ===\n(RAG disabled: Embedding API not open)\n\n"
                        "=== RECENT EXPERIENCES ===\n(RAG disabled)\n\n"
                        "=== EXPERIENCE SUMMARIES ===\n(RAG disabled)\n\n"
                        "=== ARCHIVED EXPERIENCES ===\n(RAG disabled)"
                    )
                return "=== KNOWLEDGE BASE ===\n(RAG disabled: Embedding API not open)"

            logger.error(f"RAG Retrieval failed: {e}")
            self.retrieval_enabled = False
            self.memory_enabled = False
            self.disabled_reason = str(e)
            return "RAG Retrieval failed due to an error."

    def add_experience(
        self,
        hypothesis: str,
        code: str,
        metrics: Dict[str, float],
        is_effective: bool,
        review: str,
        suggested_improvements: str = "",
        is_simulated: bool = False,
        evaluation_mode: str = "unknown",
        market_regime: str = "",
        iteration: int = 0,
        hypothesis_name: str = "",
        role_prompt: str = "",
    ):
        if not self.memory_enabled:
            logger.warning(f"Skipping experience write because RAG memory is disabled: {self.disabled_reason}")
            return
        try:
            with self._experience_lock():
                entry = self._normalize_experience_entry(
                    {
                        "entry_id": f"exp_{uuid.uuid4().hex}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "iteration": iteration,
                        "hypothesis_name": hypothesis_name,
                        "hypothesis": hypothesis,
                        "code": code,
                        "metrics": metrics,
                        "is_effective": is_effective,
                        "is_simulated": is_simulated,
                        "review": review,
                        "suggested_improvements": suggested_improvements,
                        "evaluation_mode": evaluation_mode,
                        "market_regime": market_regime,
                        "role_prompt": role_prompt,
                        "source": "live_eval",
                    }
                )
                self._append_experience_entry_locked(entry)
                self._refresh_experience_layers_locked()
                logger.info(
                    "Added layered experience {} ({}/{})".format(
                        entry["entry_id"],
                        entry["factor_family"],
                        entry["failure_type"],
                    )
                )
        except Exception as e:
            self.memory_enabled = False
            self.disabled_reason = str(e)
            logger.error(f"Failed to add experience to layered RAG memory: {e}")
