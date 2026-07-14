import os
import json
import glob
import uuid
import shutil
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, cast, Optional
import chromadb
import sqlite3
from loguru import logger
from aiminer.core.chroma_lock import chroma_process_lock
from aiminer.core.interfaces import VectorStore
from aiminer.core.settings import AiminerSettings, build_settings
from aiminer.core.llm import get_llm_config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Prevent CUDA fragmentation and set higher networking timeouts
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["OPENAI_TIMEOUT"] = "60"
os.environ["HTTP_TIMEOUT"] = "60"


def resolve_embedding_model_tag(embedding_provider: str = None, *, use_gpu: bool = False) -> str:
    """Resolve the Chroma subdirectory tag without initializing embeddings."""
    use_local = (embedding_provider == "local") or (
        os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true"
    )
    if use_local:
        return "Qwen_Qwen3-Embedding-4B"

    embedding_defaults = {
        "kimi": "embedding-2",
        "qwen": "text-embedding-v3",
        "claude": "text-embedding-3-small",
        "glm": "embedding-3",
        "openai": "text-embedding-3-large",
        "ollama": "nomic-embed-text",
        "vllm": "BAAI_bge-large-zh-v1.5",
    }
    try:
        cfg = get_llm_config(provider=embedding_provider)
        provider = cfg["provider"]
        model_name = embedding_defaults[provider]
        return f"{provider}_{model_name.replace('/', '_')}"
    except (ValueError, KeyError):
        return "bge-large"


def chroma_sqlite_summary(db_root: str, model_tag: str) -> Dict[str, object]:
    db_dir = os.path.join(db_root, model_tag)
    sqlite_path = os.path.join(db_dir, "chroma.sqlite3")
    summary: Dict[str, object] = {
        "model_tag": model_tag,
        "db_dir": db_dir,
        "sqlite_path": sqlite_path,
        "exists": os.path.exists(sqlite_path),
        "collections": 0,
        "embeddings": 0,
        "ready": False,
    }
    if not summary["exists"]:
        return summary
    try:
        conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "collections" in tables:
                summary["collections"] = int(
                    conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0]
                )
            if "embeddings" in tables:
                summary["embeddings"] = int(
                    conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
                )
        finally:
            conn.close()
    except sqlite3.Error as exc:
        summary["error"] = str(exc)
        return summary
    summary["ready"] = int(summary["embeddings"]) > 0
    return summary


class RAGModule:
    def __init__(
        self,
        db_dir: str = "data/chroma_db",
        docs_dir: str = "data/rag_docs",
        rebuild: bool = False,
        embedding_provider: str = None,
        use_gpu: bool = False,
        settings: AiminerSettings | None = None,
    ):
        from chromadb.utils.embedding_functions import (
            OpenAIEmbeddingFunction,
            SentenceTransformerEmbeddingFunction,
        )

        self.settings = settings or build_settings(
            {"use_gpu": use_gpu, "embedding_provider": embedding_provider}
        )
        self.docs_dir = docs_dir
        self.rebuild = rebuild
        os.makedirs(self.docs_dir, exist_ok=True)
        self.knowledge_cache = []
        self.experience_cache = []
        self.disable_chroma = os.getenv("AIMINER_DISABLE_CHROMA", "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if self.disable_chroma:
            logger.warning(
                "ChromaDB is disabled via AIMINER_DISABLE_CHROMA; using lexical RAG fallback."
            )
            self.embedding_fn = None
            self.db_dir = os.path.join(db_dir, "disabled")
            os.makedirs(self.db_dir, exist_ok=True)
            self._init_knowledge_cache()
            return

        # Check if local embedding is forced
        use_local = (embedding_provider == "local") or (
            os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true"
        )

        if use_local:
            model_name = "Qwen/Qwen3-Embedding-4B"
            model_tag = model_name.replace("/", "_")  # Safe for filesystem
            device = "cuda" if use_gpu else "cpu"
            logger.info(
                f"Initializing LARGE LOCAL embedding model ({model_name}) on {device}..."
            )
            try:
                self.embedding_fn = SentenceTransformerEmbeddingFunction(
                    model_name=model_name, device=device, trust_remote_code=True
                )
            except Exception as e:
                logger.warning(
                    f"Note: Hub connection sluggish ({e}). Trying mirror fallback..."
                )
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                self.embedding_fn = SentenceTransformerEmbeddingFunction(
                    model_name=model_name, device=device, trust_remote_code=True
                )
        else:
            # Auto-detect API provider
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
                "ollama": {
                    "model_name": "nomic-embed-text",
                    "api_base": os.getenv(
                        "OLLAMA_BASE_URL", "http://localhost:11434/v1"
                    ),
                },
                "vllm": {
                    "model_name": "BAAI/bge-large-zh-v1.5",
                    "api_base": os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
                },
            }

            try:
                cfg = get_llm_config(provider=embedding_provider)
                provider = cfg["provider"]
                model_tag = provider
                api_key = cfg["api_key"]
                emb_defaults = _EMBEDDING_DEFAULTS[provider]

                logger.info(f"Initializing API-based embedding ({provider})...")
                self.embedding_fn = OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=emb_defaults["model_name"],
                    api_base=emb_defaults["api_base"],
                )
                # Version by provider AND model name to prevent dimension mismatch
                model_tag = f"{provider}_{emb_defaults['model_name'].replace('/', '_')}"
            except (ValueError, KeyError):
                logger.warning(
                    "No API key or provider found for embeddings. Falling back to LOCAL bge-large."
                )
                model_tag = "bge-large"
                self.embedding_fn = SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-large-zh-v1.5"
                )

        # Version the DB directory by model_tag to avoid dimension mismatch
        self.db_dir = os.path.join(db_dir, model_tag)
        os.makedirs(self.db_dir, exist_ok=True)

        with chroma_process_lock("rag init"):
            if not self.rebuild:
                self._repair_unhealthy_chroma_collections(
                    ("knowledge_base", "experiences")
                )

            # Initialize ChromaDB
            self.client = chromadb.PersistentClient(path=self.db_dir)

            # Get or create collections with the embedding function
            self.experiences_col: VectorStore = cast(
                VectorStore,
                self.client.get_or_create_collection(
                    "experiences", embedding_function=self.embedding_fn
                ),
            )
            self.knowledge_col: VectorStore = cast(
                VectorStore,
                self.client.get_or_create_collection(
                    "knowledge_base", embedding_function=self.embedding_fn
                ),
            )

            self._init_knowledge_base()

    def _probe_collection_health(self, collection_name: str, timeout: int = 20) -> bool:
        """Probe a persisted collection in a child process.

        ChromaDB 1.5.x can segfault in native Rust bindings when a persisted
        HNSW collection is corrupt. A Python try/except cannot catch that, so
        the probe runs out-of-process and treats any non-zero exit as unsafe.
        """
        probe_code = """
import sys
import chromadb

client = chromadb.PersistentClient(path=sys.argv[1])
names = {collection.name for collection in client.list_collections()}
if sys.argv[2] not in names:
    raise SystemExit(0)
collection = client.get_collection(sys.argv[2])
collection.get(limit=1, include=["documents"])
collection.count()
"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", probe_code, self.db_dir, collection_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                f"ChromaDB collection health probe timed out: {collection_name}"
            )
            return False

        if result.returncode == 0:
            return True

        stderr_tail = result.stderr.strip().splitlines()[-3:]
        logger.warning(
            "ChromaDB collection health probe failed for "
            f"{collection_name} with exit code {result.returncode}: "
            + " | ".join(stderr_tail)
        )
        return False

    def _delete_collection_out_of_process(
        self, collection_name: str, timeout: int = 20
    ) -> bool:
        delete_code = """
import sys
import chromadb

client = chromadb.PersistentClient(path=sys.argv[1])
names = {collection.name for collection in client.list_collections()}
if sys.argv[2] in names:
    client.delete_collection(sys.argv[2])
"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", delete_code, self.db_dir, collection_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Timed out deleting ChromaDB collection: {collection_name}")
            return False

        if result.returncode == 0:
            return True

        stderr_tail = result.stderr.strip().splitlines()[-3:]
        logger.warning(
            "Failed to delete unhealthy ChromaDB collection "
            f"{collection_name} with exit code {result.returncode}: "
            + " | ".join(stderr_tail)
        )
        return False

    def _quarantine_chroma_dir(self):
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir, exist_ok=True)
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        quarantine_dir = f"{self.db_dir}.corrupt.{timestamp}"
        logger.warning(
            f"Quarantining unhealthy ChromaDB directory {self.db_dir} -> {quarantine_dir}"
        )
        shutil.move(self.db_dir, quarantine_dir)
        os.makedirs(self.db_dir, exist_ok=True)

    def _repair_unhealthy_chroma_collections(self, collection_names):
        sqlite_path = os.path.join(self.db_dir, "chroma.sqlite3")
        if not os.path.exists(sqlite_path):
            return

        for collection_name in collection_names:
            if self._probe_collection_health(collection_name):
                continue

            logger.warning(
                f"Recreating unhealthy ChromaDB collection: {collection_name}"
            )
            if self._delete_collection_out_of_process(collection_name):
                continue

            self._quarantine_chroma_dir()
            return

    def _chunk_text(
        self, text: str, chunk_size: int = 1500, overlap: int = 200
    ) -> List[str]:
        """Simple fallback text chunker splitting by size and paragraphs."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If a single paragraph is larger than chunk size, just add it directly (or we could split by sentence)
                if len(p) > chunk_size:
                    chunks.append(p)
                    current_chunk = ""
                else:
                    current_chunk = p + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _iter_doc_files(self):
        doc_files = []
        for ext in ("*.md", "*.rst", "*.txt"):
            doc_files.extend(
                glob.glob(os.path.join(self.docs_dir, "**", ext), recursive=True)
            )
        return doc_files

    def _init_knowledge_cache(self):
        self.knowledge_cache = []
        for file_path in self._iter_doc_files():
            try:
                rel_path = os.path.relpath(file_path, self.docs_dir)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for chunk in self._chunk_text(content):
                    if chunk.strip():
                        self.knowledge_cache.append(
                            {"document": chunk, "source": rel_path}
                        )
            except Exception as exc:
                logger.error(f"Failed to load lexical RAG document {file_path}: {exc}")
        logger.info(
            f"Lexical RAG cache initialized with {len(self.knowledge_cache)} chunks."
        )

    @staticmethod
    def _lexical_score(query: str, text: str) -> int:
        terms = [
            term
            for term in query.lower().replace("_", " ").split()
            if len(term) > 1
        ]
        text_lower = text.lower()
        return sum(text_lower.count(term) for term in terms)

    def _retrieve_from_cache(self, query: str, n_results: int = 2) -> str:
        scored = []
        for item in self.knowledge_cache:
            score = self._lexical_score(query, item["document"])
            if score > 0:
                scored.append((score, item["document"]))
        scored.sort(key=lambda item: item[0], reverse=True)

        context_parts = ["=== KNOWLEDGE BASE ==="]
        if scored:
            for _, doc in scored[:n_results]:
                context_parts.append(f"- {doc}")
        else:
            context_parts.append("No relevant knowledge found.")

        context_parts.append("\n=== PAST EXPERIENCES ===")
        if self.experience_cache:
            for doc in self.experience_cache[-n_results:]:
                context_parts.append(f"- {doc}")
        else:
            context_parts.append("No relevant past experiences found.")
        return "\n".join(context_parts)

    def _init_knowledge_base(self):
        # Loads actual markdown/rst/txt docs from data/rag_docs into ChromaDB.
        if self.rebuild and self.knowledge_col.count() > 0:
            logger.info("Rebuilding knowledge base: deleting existing documents...")
            self.client.delete_collection("knowledge_base")
            self.knowledge_col = self.client.get_or_create_collection(
                "knowledge_base", embedding_function=self.embedding_fn
            )

        if self.knowledge_col.count() > 0:
            logger.info(
                f"Knowledge base already initialized with {self.knowledge_col.count()} documents."
            )
            return

        logger.info(f"Scanning {self.docs_dir} for knowledge base documents...")

        doc_files = self._iter_doc_files()

        if not doc_files:
            logger.warning(f"No documents found in {self.docs_dir}.")
            return

        all_chunks = []
        all_metadatas = []
        all_ids = []

        doc_id_counter = 0

        for file_path in doc_files:
            try:
                # Extract metadata from path (e.g., data/rag_docs/academic/2026/file.md)
                # We look for yearly patterns like 2021-2026
                rel_path = os.path.relpath(file_path, self.docs_dir)
                path_parts = rel_path.split(os.sep)
                
                metadata = {"source": file_path}
                
                # Simple heuristic for type and year
                if len(path_parts) >= 1:
                    metadata["type"] = path_parts[0]
                if len(path_parts) >= 2:
                    # Check if second part is a year
                    if path_parts[1].isdigit() and len(path_parts[1]) == 4:
                        metadata["year"] = path_parts[1]
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = self._chunk_text(content)
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    all_chunks.append(chunk)
                    
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk"] = i
                    all_metadatas.append(chunk_metadata)
                    
                    all_ids.append(f"doc_{doc_id_counter}")
                    doc_id_counter += 1
            except Exception as e:
                logger.error(f"Failed to read/process {file_path}: {e}")

        if all_chunks:
            logger.info(f"Loading {len(all_chunks)} chunks into knowledge base...")
            try:
                # Small batch size to avoid OOM on 11GB GPUs
                batch_size = 8
                for i in range(0, len(all_chunks), batch_size):
                    self.knowledge_col.add(
                        documents=all_chunks[i : i + batch_size],
                        metadatas=all_metadatas[i : i + batch_size],
                        ids=all_ids[i : i + batch_size],
                    )
                logger.info("Knowledge base successfully populated.")
            except Exception as e:
                logger.error(f"Failed to populate knowledge base: {e}")

    def _safe_query(self, collection, query: str, n_results: int, max_retries: int = 3):
        # Query a collection safely with retry logic, backoff, and process-level lock protection.
        import time
        last_error = None

        for attempt in range(max_retries):
            try:
                with chroma_process_lock("rag query"):
                    count = collection.count()
                    if count == 0:
                        return None
                    actual_n = min(n_results, count)

                    # Executing the query with potential timeout
                    return collection.query(query_texts=[query], n_results=actual_n)

            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                
                # If it's a timeout or locking error, wait and retry
                if any(x in err_msg for x in ["timeout", "timed out", "rate limit", "database is locked"]):
                    wait_time = (attempt + 1) * 2
                    logger.warning(
                        f"ChromaDB query timed out or locked (Attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                    continue
                
                # For other errors, log and return empty
                logger.warning(f"ChromaDB query failed with non-timeout error: {e}. Returning empty results.")
                return None
                
        logger.error(f"ChromaDB query failed after {max_retries} retries. Final error: {last_error}")
        return None

    def retrieve(self, query: str, n_results: int = 2) -> str:
        # Retrieve relevant context from knowledge and experiences based on query.
        if self.disable_chroma:
            return self._retrieve_from_cache(query, n_results)

        try:
            # Retrieve knowledge
            k_results = self._safe_query(self.knowledge_col, query, n_results)

            # Retrieve experiences
            e_results = self._safe_query(self.experiences_col, query, n_results)

            context_parts = []

            context_parts.append("=== KNOWLEDGE BASE ===")
            if k_results and k_results["documents"] and k_results["documents"][0]:
                for doc in k_results["documents"][0]:
                    context_parts.append(f"- {doc}")
            else:
                context_parts.append("No relevant knowledge found.")

            context_parts.append("\n=== PAST EXPERIENCES ===")
            if e_results and e_results["documents"] and e_results["documents"][0]:
                for doc in e_results["documents"][0]:
                    context_parts.append(f"- {doc}")
            else:
                context_parts.append("No relevant past experiences found.")

            return "\n".join(context_parts)

        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg or "not open" in err_msg.lower():
                logger.warning(
                    "RAG Embedding API is not enabled for this provider (Kimi/Other). Running without RAG context."
                )
                return "=== KNOWLEDGE BASE ===\n(RAG disabled: Embedding API not open)\n\n=== PAST EXPERIENCES ===\n(RAG disabled)"

            logger.error(f"RAG Retrieval failed: {e}")
            return "RAG Retrieval failed due to an error."

    def add_experience(
        self,
        hypothesis: str,
        code: str,
        metrics: Dict[str, float],
        is_effective: bool,
        review: str,
    ):
        """Embed and store backtesting experience into ChromaDB."""
        document = (
            f"Hypothesis: {hypothesis}\n"
            f"Code: {code}\n"
            f"Metrics: {json.dumps(metrics)}\n"
            f"Effective: {is_effective}\n"
            f"Review: {review}"
        )

        if self.disable_chroma:
            self.experience_cache.append(document)
            return

        try:
            with chroma_process_lock("rag add_experience"):
                exp_id = f"exp_{uuid.uuid4().hex}"

                metadata = {
                    "is_effective": is_effective,
                    "ic": metrics.get("information_coefficient", 0.0),
                    "rank_ic": metrics.get("rank_ic", 0.0),
                }

                self.experiences_col.add(
                    documents=[document], metadatas=[metadata], ids=[exp_id]
                )
                logger.info(f"Added experience {exp_id} to ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to add experience to RAG: {e}")
