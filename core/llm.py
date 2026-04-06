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
    if provider == "kimi":
        return {"provider": "kimi", "api_key": os.getenv("LLM_KEY")}
    elif provider == "qwen":
        return {"provider": "qwen", "api_key": os.getenv("QWEN_API_KEY")}
    elif provider == "claude":
        return {"provider": "claude", "api_key": os.getenv("ClaudeCode_KEY")}

    kimi_key = os.getenv("LLM_KEY")
    qwen_key = os.getenv("QWEN_API_KEY")
    claude_key = os.getenv("ClaudeCode_KEY")
    
    if kimi_key:
        return {"provider": "kimi", "api_key": kimi_key}
    elif qwen_key:
        return {"provider": "qwen", "api_key": qwen_key}
    elif claude_key:
        return {"provider": "claude", "api_key": claude_key}
    else:
        raise ValueError("No LLM API key found. Set LLM_KEY, QWEN_API_KEY or ClaudeCode_KEY.")

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
    else: # claude proxy
        base_url = "https://api.gptsapi.net/v1"
        if not model_name: model_name = "claude-opus-4-6"

    logger.info(f"Using LLM Provider: {provider}, Model: {model_name}")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        max_retries=3
    )
