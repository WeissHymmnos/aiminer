import os
from typing import Dict
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm_config(provider: str = None) -> Dict[str, str]:
    """
    Returns LLM provider configuration based on available API keys.
    If 'provider' is specified, uses that provider specifically.
    """
    providers = {
        "kimi": os.getenv("LLM_KEY") or os.getenv("KIMI_API_KEY"),
        "qwen": os.getenv("QWEN_API_KEY"),
        "claude": os.getenv("ClaudeCode_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        "glm": os.getenv("GLM_KEY") or os.getenv("ZHIPU_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "deepseek": os.getenv("DEEPSEEK_API_KEY"),
        "openrouter": os.getenv("OPENROUTER_API_KEY"),
        "groq": os.getenv("GROQ_API_KEY"),
        "ollama": os.getenv("OLLAMA_API_KEY", "ollama"), # Default for local
        "vllm": os.getenv("VLLM_API_KEY", "vllm") # Default for local
    }

    if provider:
        if provider in providers:
            return {"provider": provider, "api_key": providers[provider]}
        raise ValueError(f"Unknown LLM provider requested: {provider}")

    # Auto-detect fallback
    for name, key in providers.items():
        if key and key not in ("ollama", "vllm"):
            return {"provider": name, "api_key": key}
            
    raise ValueError("No LLM API key found. Please set an appropriate environment variable (e.g. DEEPSEEK_API_KEY, OPENAI_API_KEY).")

def get_llm(temperature: float = 0.7, model_name: str = None, provider: str = None) -> BaseChatModel:
    """
    Returns a configured LangChain Chat model.
    """
    try:
        cfg = get_llm_config(provider=provider)
    except ValueError as e:
        logger.error(f"LLM Configuration failed: {e}")
        raise
        
    provider = cfg["provider"]
    api_key = cfg["api_key"]
    
    if not api_key:
        raise ValueError(f"API key for {provider} is not set in environment variables.")

    # Defaults and Model Mapping
    if provider == "kimi":
        base_url = "https://api.moonshot.cn/v1"
        if not model_name: model_name = "kimi-k2-thinking-turbo"
    elif provider == "qwen":
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        if not model_name: model_name = "qwen-max"
    elif provider == "glm":
        base_url = "https://open.bigmodel.cn/api/paas/v4"
        if not model_name: model_name = "glm-5"
    elif provider == "openai":
        base_url = "https://api.openai.com/v1"
        if not model_name: model_name = "gpt-4o"
    elif provider == "deepseek":
        base_url = "https://api.deepseek.com/v1"
        if not model_name: model_name = "deepseek-reasoner"
    elif provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
        if not model_name: model_name = "deepseek/deepseek-r1"
    elif provider == "groq":
        base_url = "https://api.groq.com/openai/v1"
        if not model_name: model_name = "llama-3.3-70b-versatile"
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        if not model_name: model_name = "deepseek-r1:14b"
    elif provider == "vllm":
        base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        if not model_name: model_name = "meta-llama/Llama-3-70b-chat-hf"
    else: # claude proxy
        base_url = "https://api.gptsapi.net/v1"
        if not model_name: model_name = "claude-3-5-sonnet-20241022"

    logger.info(f"Using LLM Provider: {provider}, Model: {model_name}")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        max_retries=3
    )
