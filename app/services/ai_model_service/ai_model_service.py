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


def register_provider(provider: AIModelProvider) -> None:
    global _provider
    _provider = provider
    logger.info("AI provider registered: %s", provider.name)


def get_provider() -> AIModelProvider:
    if _provider is None:
        raise RuntimeError(
            "No AI provider registered. "
            "Call ai_model_service.register_provider(...) inside create_app()."
        )
    return _provider


def complete(prompt: str) -> str:
    """Route a prompt through the registered provider."""
    return get_provider().complete(prompt)
