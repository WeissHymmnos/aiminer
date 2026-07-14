import os
from typing import Dict
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from aiminer.core.settings import detect_llm_provider, provider_api_key


def _normalize_mimo_model(model_name: str | None) -> str:
    if not model_name:
        return "mimo-v2.5-pro"

    raw = model_name.strip()
    normalized = raw.lower().replace("_", "-")
    compact = normalized.replace(" ", "-")
    aliases = {
        "mimo-v2.5pro": "mimo-v2.5-pro",
        "mimo-v2.5-pro": "mimo-v2.5-pro",
        "mimo-v2.5": "mimo-v2.5",
        "mimo-v25pro": "mimo-v2.5-pro",
        "mimo-v25-pro": "mimo-v2.5-pro",
        "mimo-v25": "mimo-v2.5",
        "xiaomi/mimo-v2.5-pro": "mimo-v2.5-pro",
        "xiaomi/mimo-v2.5": "mimo-v2.5",
    }
    return aliases.get(compact, raw)


def get_llm_config(provider: str = None) -> Dict[str, str]:
    """
    Returns LLM provider configuration based on available API keys.
    If 'provider' is specified, uses that provider specifically.
    """
    if provider:
        api_key = provider_api_key(provider)
        if api_key is not None:
            return {"provider": provider, "api_key": api_key}
        raise ValueError(f"Unknown LLM provider requested: {provider}")

    # Auto-detect fallback
    detected = detect_llm_provider()
    if detected:
        return {"provider": detected, "api_key": provider_api_key(detected)}

    raise ValueError(
        "No LLM API key found. Please set an appropriate environment variable (e.g. DEEPSEEK_API_KEY, OPENAI_API_KEY)."
    )


def get_llm(
    temperature: float = 0.7,
    model_name: str = None,
    provider: str = None,
    base_url: str = None,
    reasoning_effort: str = None,
) -> BaseChatModel:
    """
    Returns a configured LangChain Chat model.
    """
    try:
        cfg = get_llm_config(provider=provider)
    except ValueError as e:
        if provider == "openai" and base_url:
            cfg = {"provider": provider, "api_key": "openai-compatible"}
        else:
            logger.error(f"LLM Configuration failed: {e}")
            raise

    provider = cfg["provider"]
    api_key = cfg["api_key"]

    if provider == "codex":
        if base_url:
            logger.warning("llm_base_url is ignored when llm_provider='codex'.")
        from aiminer.core.codex_llm import CodexChatModel

        logger.info(f"Using LLM Provider: codex, Model: {model_name or 'gpt-5.4'}")
        return CodexChatModel(
            model_name=model_name or "gpt-5.4",
            temperature=temperature,
            reasoning_effort=reasoning_effort,
        )

    if not api_key and provider == "openai" and base_url:
        api_key = "openai-compatible"

    if not api_key:
        raise ValueError(f"API key for {provider} is not set in environment variables.")

    # Defaults and Model Mapping
    if provider == "kimi":
        resolved_base_url = base_url or "https://api.moonshot.cn/v1"
        if not model_name:
            model_name = "kimi-k2-turbo-preview"
    elif provider == "qwen":
        resolved_base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        if not model_name:
            model_name = "qwen-max"
    elif provider == "glm":
        resolved_base_url = base_url or "https://open.bigmodel.cn/api/paas/v4"
        if not model_name:
            model_name = "glm-5"
    elif provider == "openai":
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        if not model_name:
            model_name = "gpt-4o"
    elif provider == "deepseek":
        resolved_base_url = base_url or "https://api.deepseek.com/v1"
        if not model_name:
            model_name = "deepseek-v4-flash"
    elif provider == "mimo":
        resolved_base_url = (
            base_url
            or os.getenv("MIMO_BASE_URL")
            or "https://token-plan-cn.xiaomimimo.com/v1"
        )
        model_name = _normalize_mimo_model(model_name)
    elif provider == "openrouter":
        resolved_base_url = base_url or "https://openrouter.ai/api/v1"
        if not model_name:
            model_name = "deepseek/deepseek-r1"
    elif provider == "groq":
        resolved_base_url = base_url or "https://api.groq.com/openai/v1"
        if not model_name:
            model_name = "llama-3.3-70b-versatile"
    elif provider == "ollama":
        resolved_base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        if not model_name:
            model_name = "deepseek-r1:14b"
    elif provider == "vllm":
        resolved_base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        if not model_name:
            model_name = "meta-llama/Llama-3-70b-chat-hf"
    elif provider == "lmstudio":
        resolved_base_url = (
            base_url
            or os.getenv("LMSTUDIO_BASE_URL")
            or os.getenv("LM_STUDIO_BASE_URL")
            or "http://127.0.0.1:1234/v1"
        )
        if not model_name:
            model_name = "local-model"
    elif provider == "claude":
        resolved_base_url = base_url or "https://api.gptsapi.net/v1"
        if not model_name:
            model_name = "claude-3-5-sonnet-20241022"
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    logger.info(f"Using LLM Provider: {provider}, Model: {model_name}")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=resolved_base_url,
        max_retries=3,
        request_timeout=180,
    )
