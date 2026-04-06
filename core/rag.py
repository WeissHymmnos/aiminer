import os
import json
import glob
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction, SentenceTransformerEmbeddingFunction
from loguru import logger
from core.llm import get_llm_config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Prevent CUDA fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

class RAGModule:
    def __init__(self, db_dir: str = "data/chroma_db", docs_dir: str = "data/rag_docs", rebuild: bool = False, embedding_provider: str = None, use_gpu: bool = False):
        self.docs_dir = docs_dir
        self.rebuild = rebuild
        os.makedirs(self.docs_dir, exist_ok=True)
        
        # Check if local embedding is forced
        use_local = (embedding_provider == "local") or (os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true")
        
        model_tag = "api"
        if use_local:
            model_name = "Qwen/Qwen3-Embedding-4B"
            model_tag = model_name.replace("/", "_") # Safe for filesystem
            device = "cuda" if use_gpu else "cpu"
            logger.info(f"Initializing LARGE LOCAL embedding model ({model_name}) on {device}...")
            try:
                self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name=model_name, device=device, trust_remote_code=True)
            except Exception as e:
                logger.warning(f"Note: Hub connection sluggish ({e}). Trying mirror fallback...")
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
                self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name=model_name, device=device, trust_remote_code=True)
        else:
            # Auto-detect API provider
            _EMBEDDING_DEFAULTS = {
                "kimi": {"model_name": "embedding-2", "api_base": "https://api.moonshot.cn/v1"},
                "qwen": {"model_name": "text-embedding-v3", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
                "claude": {"model_name": "text-embedding-3-small", "api_base": "https://api.gptsapi.net/v1"},
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
            except (ValueError, KeyError):
                logger.warning("No API key or provider found for embeddings. Falling back to LOCAL bge-large.")
                model_tag = "bge-large"
                self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-zh-v1.5")

        # Version the DB directory by model_tag to avoid dimension mismatch
        self.db_dir = os.path.join(db_dir, model_tag)
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=self.db_dir)
        
        # Get or create collections with the embedding function
        self.experiences_col = self.client.get_or_create_collection(
            "experiences", embedding_function=self.embedding_fn
        )
        self.knowledge_col = self.client.get_or_create_collection(
            "knowledge_base", embedding_function=self.embedding_fn
        )
        
        # Local cache for keyword search fallback
        self.knowledge_cache = []
        
        self._init_knowledge_base()

    def _chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        """Simple fallback text chunker splitting by size and paragraphs."""
        paragraphs = text.split('\n\n')
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

    def _init_knowledge_base(self):
        #Loads actual markdown/rst/txt docs from data/rag_docs into ChromaDB.        
        if self.rebuild and self.knowledge_col.count() > 0:
            logger.info("Rebuilding knowledge base: deleting existing documents...")
            self.client.delete_collection("knowledge_base")
            self.knowledge_col = self.client.get_or_create_collection(
                "knowledge_base", embedding_function=self.embedding_fn
            )

        if self.knowledge_col.count() > 0 :
            logger.info(f"Knowledge base already initialized with {self.knowledge_col.count()} documents.")
            return
            
        logger.info(f"Scanning {self.docs_dir} for knowledge base documents...")
        
        doc_files = []
        for ext in ('*.md', '*.rst', '*.txt'):
            doc_files.extend(glob.glob(os.path.join(self.docs_dir, '**', ext), recursive=True))
            
        if not doc_files:
            logger.warning(f"No documents found in {self.docs_dir}.")
            return
            
        all_chunks = []
        all_metadatas = []
        all_ids = []
        
        doc_id_counter = 0
        
        for file_path in doc_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                chunks = self._chunk_text(content)
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    all_chunks.append(chunk)
                    all_metadatas.append({"source": file_path, "chunk": i})
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
                        documents=all_chunks[i:i+batch_size],
                        metadatas=all_metadatas[i:i+batch_size],
                        ids=all_ids[i:i+batch_size]
                    )
                logger.info("Knowledge base successfully populated.")
            except Exception as e:
                logger.error(f"Failed to populate knowledge base: {e}")

    def _safe_query(self, collection, query: str, n_results: int):
        # Query a collection safely, handling empty collections.
        count = collection.count()
        if count == 0:
            return None
        actual_n = min(n_results, count)
        return collection.query(query_texts=[query], n_results=actual_n)

    def retrieve(self, query: str, n_results: int = 2) -> str:
        # Retrieve relevant context from knowledge and experiences based on query.
        try:
            # Retrieve knowledge
            k_results = self._safe_query(self.knowledge_col, query, n_results)
            
            # Retrieve experiences
            e_results = self._safe_query(self.experiences_col, query, n_results)
            
            context_parts = []
            
            context_parts.append("=== KNOWLEDGE BASE ===")
            if k_results and k_results['documents'] and k_results['documents'][0]:
                for doc in k_results['documents'][0]:
                    context_parts.append(f"- {doc}")
            else:
                context_parts.append("No relevant knowledge found.")
                
            context_parts.append("\n=== PAST EXPERIENCES ===")
            if e_results and e_results['documents'] and e_results['documents'][0]:
                for doc in e_results['documents'][0]:
                    context_parts.append(f"- {doc}")
            else:
                context_parts.append("No relevant past experiences found.")
                
            return "\n".join(context_parts)
            
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg or "not open" in err_msg.lower():
                logger.warning("RAG Embedding API is not enabled for this provider (Kimi/Other). Running without RAG context.")
                return "=== KNOWLEDGE BASE ===\n(RAG disabled: Embedding API not open)\n\n=== PAST EXPERIENCES ===\n(RAG disabled)"
            
            logger.error(f"RAG Retrieval failed: {e}")
            return "RAG Retrieval failed due to an error."

    def add_experience(self, hypothesis: str, code: str, metrics: Dict[str, float], is_effective: bool, review: str):
        """Embed and store backtesting experience into ChromaDB."""
        try:
            exp_id = f"exp_{uuid.uuid4().hex}"
            
            # Create a rich document representation
            document = (
                f"Hypothesis: {hypothesis}\n"
                f"Code: {code}\n"
                f"Metrics: {json.dumps(metrics)}\n"
                f"Effective: {is_effective}\n"
                f"Review: {review}"
            )
            
            metadata = {
                "is_effective": is_effective,
                "ic": metrics.get("information_coefficient", 0.0),
                "rank_ic": metrics.get("rank_ic", 0.0)
            }
            
            self.experiences_col.add(
                documents=[document],
                metadatas=[metadata],
                ids=[exp_id]
            )
            logger.info(f"Added experience {exp_id} to ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to add experience to RAG: {e}")
