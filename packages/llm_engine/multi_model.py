"""
Multi-model LLM provider abstraction.

Supports OpenAI, Anthropic Claude, Google Gemini, and local models (Ollama/vLLM)
via a unified interface. Uses LiteLLM as the routing layer when available,
falls back to direct LangChain provider imports.

Environment variables:
    LLM_PROVIDER: openai | anthropic | google | ollama | litellm (default: openai)
    LLM_MODEL_NAME: Model name (default: gpt-4o)
    OPENAI_API_KEY: OpenAI API key
    ANTHROPIC_API_KEY: Anthropic API key
    GOOGLE_API_KEY: Google AI API key
    OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)
"""

import os
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel


# Provider registry
_PROVIDERS: Dict[str, type] = {}


def _register_providers() -> None:
    """Discover available LLM providers at import time."""
    global _PROVIDERS

    # OpenAI (always available — it's a core dependency)
    try:
        from langchain_openai import ChatOpenAI
        _PROVIDERS["openai"] = ChatOpenAI
    except ImportError:
        pass

    # Anthropic Claude
    try:
        from langchain_anthropic import ChatAnthropic
        _PROVIDERS["anthropic"] = ChatAnthropic
    except ImportError:
        pass

    # Google Gemini
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        _PROVIDERS["google"] = ChatGoogleGenerativeAI
    except ImportError:
        pass

    # Ollama (local models)
    try:
        from langchain_community.chat_models import ChatOllama
        _PROVIDERS["ollama"] = ChatOllama
    except ImportError:
        pass

    # LiteLLM (universal router — supports 100+ providers)
    try:
        from langchain_community.chat_models import ChatLiteLLM
        _PROVIDERS["litellm"] = ChatLiteLLM
    except ImportError:
        pass


_register_providers()


# Default model names per provider
_DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20241022",
    "google": "gemini-2.0-flash",
    "ollama": "llama3.2",
    "litellm": "gpt-4o",
}


def get_available_providers() -> list[str]:
    """Return list of available LLM provider names."""
    return list(_PROVIDERS.keys())


def get_chat_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.3,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Create a chat model instance for the specified provider.

    Args:
        provider: LLM provider name. Defaults to LLM_PROVIDER env var or 'openai'.
        model_name: Model name. Defaults to LLM_MODEL_NAME env var or provider default.
        temperature: Sampling temperature (default: 0.3).
        **kwargs: Additional provider-specific arguments.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not available.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "openai")
    model_name = model_name or os.getenv("LLM_MODEL_NAME", _DEFAULT_MODELS.get(provider, "gpt-4o"))

    if provider not in _PROVIDERS:
        available = ", ".join(get_available_providers()) or "none"
        raise ValueError(
            f"LLM provider '{provider}' is not available. "
            f"Available providers: {available}. "
            f"Install the required package (e.g., pip install langchain-anthropic)."
        )

    model_class = _PROVIDERS[provider]

    # Provider-specific configuration
    if provider == "openai":
        return model_class(
            model=model_name,
            temperature=temperature,
            **kwargs,
        )

    elif provider == "anthropic":
        return model_class(
            model=model_name,
            temperature=temperature,
            max_tokens=kwargs.pop("max_tokens", 4096),
            **kwargs,
        )

    elif provider == "google":
        return model_class(
            model=model_name,
            temperature=temperature,
            **kwargs,
        )

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return model_class(
            model=model_name,
            temperature=temperature,
            base_url=base_url,
            **kwargs,
        )

    elif provider == "litellm":
        return model_class(
            model=model_name,
            temperature=temperature,
            **kwargs,
        )

    # Fallback — try generic instantiation
    return model_class(
        model=model_name,
        temperature=temperature,
        **kwargs,
    )


def get_model_info() -> Dict[str, Any]:
    """Return information about the current LLM configuration."""
    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("LLM_MODEL_NAME", _DEFAULT_MODELS.get(provider, "gpt-4o"))
    return {
        "provider": provider,
        "model_name": model_name,
        "available_providers": get_available_providers(),
        "default_models": _DEFAULT_MODELS,
    }
