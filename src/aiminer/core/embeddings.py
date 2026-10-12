"""Embedding backend resolution.

Chat-only providers (deepseek, mimo, groq, ...) must not inherit the OpenAI /
gptsapi embedding endpoint — that combination 401s on upsert.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

LOCAL_BGE = "BAAI/bge-large-zh-v1.5"
LOCAL_QWEN = "Qwen/Qwen3-Embedding-4B"
# Chat-only providers: no /v1/embeddings. Do not fall through to gptsapi.
_CHAT_ONLY_PROVIDERS = frozenset(
    {"deepseek", "mimo", "groq", "openrouter", "lmstudio", "codex"}
)

EMBEDDING_API_DEFAULTS: dict[str, dict[str, str]] = {
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
        "api_base": os.getenv("OPENAI_BASE_URL") or "https://api.gptsapi.net/v1",
    },
    "ollama": {
        "model_name": "nomic-embed-text",
        "api_base": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    },
    "vllm": {
        "model_name": "BAAI/bge-large-zh-v1.5",
        "api_base": os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
    },
}


def _use_forced_local(embedding_provider: str | None) -> bool:
    if (embedding_provider or "").strip().lower() == "local":
        return True
    return os.getenv("USE_LOCAL_EMBEDDING", "false").lower() == "true"


def resolve_embedding_backend(embedding_provider: str | None = None) -> dict[str, Any]:
    """Pick a working embedding backend.

    Providers without a real embeddings API (notably DeepSeek / CPA chat)
    return a local SentenceTransformer backend instead of borrowing gptsapi.
    """
    if _use_forced_local(embedding_provider):
        tag = LOCAL_QWEN.replace("/", "_")
        return {
            "mode": "local",
            "provider": "local",
            "model_name": LOCAL_QWEN,
            "model_tag": tag,
            "api_key": None,
            "api_base": None,
        }

    requested = (embedding_provider or "").strip().lower()
    if requested in _CHAT_ONLY_PROVIDERS:
        logger.warning(
            "Provider {!r} has no embeddings endpoint; using local {}",
            requested,
            LOCAL_BGE,
        )
        return {
            "mode": "local",
            "provider": requested,
            "model_name": LOCAL_BGE,
            "model_tag": "bge-large",
            "api_key": None,
            "api_base": None,
        }

    try:
        from aiminer.core.llm import get_llm_config

        cfg = get_llm_config(provider=embedding_provider)
    except ValueError:
        logger.warning(
            "No embedding API key/provider; using local {}", LOCAL_BGE
        )
        return {
            "mode": "local",
            "provider": "local",
            "model_name": LOCAL_BGE,
            "model_tag": "bge-large",
            "api_key": None,
            "api_base": None,
        }

    provider = str(cfg["provider"])
    defaults = EMBEDDING_API_DEFAULTS.get(provider)
    if defaults is None:
        logger.warning(
            "Provider {!r} has no embeddings endpoint; using local {}",
            provider,
            LOCAL_BGE,
        )
        return {
            "mode": "local",
            "provider": provider,
            "model_name": LOCAL_BGE,
            "model_tag": "bge-large",
            "api_key": None,
            "api_base": None,
        }

    model_name = defaults["model_name"]
    return {
        "mode": "api",
        "provider": provider,
        "model_name": model_name,
        "model_tag": f"{provider}_{model_name.replace('/', '_')}",
        "api_key": cfg["api_key"],
        "api_base": defaults["api_base"],
    }
