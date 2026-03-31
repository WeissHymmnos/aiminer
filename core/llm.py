import os
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm_config() -> Dict[str, str]:
    """
    Returns LLM provider configuration based on available API keys.
    Returns dict with 'provider' and 'api_key'.
    Raises ValueError if no API key is found.
    """
    qwen_key = os.getenv("QWEN_API_KEY")
    claude_key = os.getenv("ClaudeCode_KEY")
    
    if qwen_key:
        return {"provider": "qwen", "api_key": qwen_key}
    elif claude_key:
        return {"provider": "claude", "api_key": claude_key}
    else:
        raise ValueError("No LLM API key found. Set QWEN_API_KEY or ClaudeCode_KEY.")

def get_llm(temperature: float = 0.7, model_name: str = "claude-opus-4-6") -> BaseChatModel:
    """
    Returns a configured LangChain Chat model (Claude 4.6 via Proxy).
    Note: We use ChatOpenAI because gptsapi.net is an OpenAI-compatible aggregator.
    """
    api_key = os.getenv("ClaudeCode_KEY")
    if not api_key:
        raise ValueError("ClaudeCode_KEY environment variable is not set. Please ensure it's in your .env or environment.")
    
    # Use the proxy base_url with /v1 suffix for OpenAI compatibility
    base_url = "https://api.gptsapi.net/v1"
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        max_retries=3
    )
