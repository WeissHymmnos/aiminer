import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

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
