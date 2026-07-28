"""Multi-provider LLM gateway.

Returns LangChain-compatible chat clients. Provider credentials and optional
base-URL overrides are read from environment variables (see ``.env.example``).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

# Canonical env aliases for each provider (first match wins).
_PROVIDER_KEY_ENVS: Dict[str, tuple[str, ...]] = {
    "kimi": ("KIMI_API_KEY", "LLM_KEY"),
    "qwen": ("QWEN_API_KEY",),
    "claude": ("ANTHROPIC_API_KEY", "ClaudeCode_KEY"),
    "glm": ("ZHIPU_API_KEY", "GLM_KEY"),
    "openai": ("OPENAI_API_KEY", "OpenAI_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "ollama": ("OLLAMA_API_KEY",),
    "vllm": ("VLLM_API_KEY",),
}

# Default OpenAI-compatible base URLs. Override with ``{PROVIDER}_BASE_URL``
# (e.g. ``CLAUDE_BASE_URL``) or the shared ``LLM_BASE_URL`` when needed.
_PROVIDER_BASE_URLS: Dict[str, str] = {
    "kimi": "https://api.moonshot.cn/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "glm": "https://open.bigmodel.cn/api/paas/v4",
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    # Claude: OpenAI-compatible gateway. Prefer official Anthropic via
    # CLAUDE_BASE_URL if you use a proxy; default points at Anthropic's
    # OpenAI-compat layer when available, else set CLAUDE_BASE_URL explicitly.
    "claude": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434/v1",
    "vllm": "http://localhost:8000/v1",
}

_PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "kimi": "kimi-k2-turbo-preview",
    "qwen": "qwen-max",
    "glm": "glm-5",
    "openai": "gpt-4o",
    "deepseek": "deepseek-reasoner",
    "openrouter": "deepseek/deepseek-r1",
    "groq": "llama-3.3-70b-versatile",
    "claude": "claude-sonnet-4-20250514",
    "ollama": "deepseek-r1:14b",
    "vllm": "meta-llama/Llama-3-70b-chat-hf",
}

# Embedding defaults (OpenAI-compatible endpoints). Shared by RAG and Wiki.
EMBEDDING_DEFAULTS: Dict[str, Dict[str, str]] = {
    "kimi": {
        "model_name": "embedding-2",
        "api_base": "https://api.moonshot.cn/v1",
    },
    "qwen": {
        "model_name": "text-embedding-v3",
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "glm": {
        "model_name": "embedding-3",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
    },
    "openai": {
        "model_name": "text-embedding-3-large",
        "api_base": "https://api.openai.com/v1",
    },
    # Anthropic does not ship a public embeddings API comparable to OpenAI;
    # fall back to OpenAI embeddings when the chat provider is Claude.
    "claude": {
        "model_name": "text-embedding-3-small",
        "api_base": "https://api.openai.com/v1",
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

# Local sentinel values used when no real key is required.
_LOCAL_SENTINELS = frozenset({"ollama", "vllm"})


def _resolve_api_key(provider: str) -> Optional[str]:
    envs = _PROVIDER_KEY_ENVS.get(provider, ())
    for env_name in envs:
        value = os.getenv(env_name)
        if value:
            return value
    if provider in _LOCAL_SENTINELS:
        return provider  # placeholder accepted by local OpenAI-compatible servers
    return None


def get_provider_base_url(provider: str) -> str:
    """Resolve base URL with env overrides.

    Priority: ``{PROVIDER}_BASE_URL`` → ``LLM_BASE_URL`` → built-in default.
    Also honors legacy ``OLLAMA_BASE_URL`` / ``VLLM_BASE_URL`` / ``ANTHROPIC_BASE_URL``.
    """
    specific = os.getenv(f"{provider.upper()}_BASE_URL")
    if specific:
        return specific
    if provider == "ollama" and os.getenv("OLLAMA_BASE_URL"):
        return os.environ["OLLAMA_BASE_URL"]
    if provider == "vllm" and os.getenv("VLLM_BASE_URL"):
        return os.environ["VLLM_BASE_URL"]
    if provider == "claude" and os.getenv("ANTHROPIC_BASE_URL"):
        return os.environ["ANTHROPIC_BASE_URL"]
    shared = os.getenv("LLM_BASE_URL")
    if shared:
        return shared
    return _PROVIDER_BASE_URLS[provider]


def get_llm_config(provider: Optional[str] = None) -> Dict[str, str]:
    """Return ``{"provider", "api_key"}`` for the requested or auto-detected provider."""
    if provider:
        if provider not in _PROVIDER_KEY_ENVS:
            raise ValueError(f"Unknown LLM provider requested: {provider}")
        api_key = _resolve_api_key(provider)
        return {"provider": provider, "api_key": api_key}

    for name in _PROVIDER_KEY_ENVS:
        key = _resolve_api_key(name)
        if key and key not in _LOCAL_SENTINELS:
            return {"provider": name, "api_key": key}

    raise ValueError(
        "No LLM API key found. Set one of: OPENAI_API_KEY, ZHIPU_API_KEY, "
        "ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, KIMI_API_KEY, QWEN_API_KEY, "
        "OPENROUTER_API_KEY, GROQ_API_KEY (see .env.example)."
    )


def get_embedding_defaults(provider: str) -> Dict[str, str]:
    """Return embedding model + api_base for a provider (falls back to OpenAI)."""
    defaults = EMBEDDING_DEFAULTS.get(provider, EMBEDDING_DEFAULTS["openai"]).copy()
    # Allow overriding embedding base URL independently.
    emb_base = os.getenv(f"{provider.upper()}_EMBEDDING_BASE_URL") or os.getenv(
        "EMBEDDING_BASE_URL"
    )
    if emb_base:
        defaults["api_base"] = emb_base
    emb_model = os.getenv(f"{provider.upper()}_EMBEDDING_MODEL") or os.getenv(
        "EMBEDDING_MODEL"
    )
    if emb_model:
        defaults["model_name"] = emb_model
    # Claude chat keys cannot call OpenAI embeddings; prefer OpenAI key when present.
    if provider == "claude":
        openai_key = _resolve_api_key("openai")
        if openai_key:
            defaults["api_key_override"] = openai_key
    return defaults


def get_llm(
    temperature: float = 0.7,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> BaseChatModel:
    """Return a configured LangChain chat model for the given provider."""
    try:
        cfg = get_llm_config(provider=provider)
    except ValueError as e:
        logger.error(f"LLM Configuration failed: {e}")
        raise

    provider = cfg["provider"]
    api_key = cfg["api_key"]

    if not api_key:
        raise ValueError(
            f"API key for provider '{provider}' is not set. "
            f"Expected one of: {', '.join(_PROVIDER_KEY_ENVS.get(provider, ()))}."
        )

    base_url = get_provider_base_url(provider)
    if not model_name:
        model_name = _PROVIDER_DEFAULT_MODELS.get(provider, "gpt-4o")

    logger.info(f"Using LLM Provider: {provider}, Model: {model_name}")

    kwargs: Dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "api_key": api_key,
        "base_url": base_url,
        "max_retries": 3,
    }
    # langchain-openai versions differ on timeout kwarg name
    try:
        return ChatOpenAI(**kwargs, request_timeout=60)
    except TypeError:
        return ChatOpenAI(**kwargs, timeout=60)
