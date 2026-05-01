"""
Backward-compatible shim.
New code should import ai_model_service.complete() directly.
"""
from app.services.ai_model_service import ai_model_service


def ask_gemma(prompt: str) -> str:
    return ai_model_service.complete(prompt)
