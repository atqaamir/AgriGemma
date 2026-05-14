"""
Central AI model registry.

Usage
-----
# In create_app():
from app.services.ai_model_service import ai_model_service
from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider

ai_model_service.register_provider(GemmaProvider())

# Anywhere in the codebase:
from app.services.ai_model_service import ai_model_service

text = ai_model_service.complete(prompt)

Swapping providers requires only a single line change in create_app().
"""
import logging
from app.services.ai_model_service.ai_provider_interface import AIModelProvider

logger = logging.getLogger(__name__)

_provider: AIModelProvider | None = None
_fast_provider: AIModelProvider | None = None


def register_provider(provider: AIModelProvider) -> None:
    """Register the main provider (chatbot — large model)."""
    global _provider
    _provider = provider
    logger.info("AI provider registered: %s", provider.name)


def register_fast_provider(provider: AIModelProvider) -> None:
    """Register the fast provider (summaries, alerts, intent — small/edge model)."""
    global _fast_provider
    _fast_provider = provider
    logger.info("Fast AI provider registered: %s", provider.name)


def get_provider() -> AIModelProvider:
    if _provider is None:
        raise RuntimeError(
            "No AI provider registered. "
            "Call ai_model_service.register_provider(...) inside create_app()."
        )
    return _provider


def complete(prompt: str) -> str:
    """Route a prompt through the main provider (chatbot)."""
    return get_provider().complete(prompt)


def stream_complete(prompt: str):
    """Stream response tokens from the main provider (chatbot)."""
    return get_provider().stream_complete(prompt)


def fast_complete(prompt: str) -> str:
    """Route a prompt through the fast provider (summaries/alerts/intent).
    Falls back to main provider if no fast provider is registered."""
    provider = _fast_provider if _fast_provider is not None else get_provider()
    return provider.complete(prompt)


def fast_stream_complete(prompt: str):
    """Stream from the fast provider. Falls back to main provider."""
    provider = _fast_provider if _fast_provider is not None else get_provider()
    return provider.stream_complete(prompt)
