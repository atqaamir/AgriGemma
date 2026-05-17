"""
Gemma 4 provider via Google AI Edge / LiteRT (MediaPipe LLM Inference Task API).

Runs Gemma 4 1B quantized model fully locally — no internet required after setup.

Setup
-----
1. Install dependency:
       pip install mediapipe>=0.10.21

2. Download the Gemma 4 1B LiteRT model from Kaggle:
       https://www.kaggle.com/models/google/gemma-4/litert/gemma4-1b-it-gpu-int4

   Place the .task file at (default):
       ~/.gemma_models/gemma4-1b-it-gpu-int4.task

   Or point to a custom path via env var:
       GEMMA_MODEL_PATH=/path/to/gemma4-1b-it-gpu-int4.task

Environment variables
---------------------
GEMMA_MODEL_PATH   — absolute path to the .task model file
"""

import os
import logging
from pathlib import Path

from app.services.ai_model_service.ai_provider_interface import AIModelProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_DIR = Path.home() / ".gemma_models"
_MODEL_FILENAME = "gemma4-1b-it-gpu-int4.task"


class GemmaProvider(AIModelProvider):
    """
    Gemma 4 1B on-device inference via Google AI Edge LiteRT.

    Uses MediaPipe LLM Inference Task API — the same runtime that powers
    Gemma on Android/iOS. Falls back to rule-based placeholder responses
    when the model file is absent so the app still runs during development.
    """

    def __init__(self, model_path: str | None = None) -> None:
        self._model = None
        self._model_path = (
            model_path
            or os.getenv("GEMMA_MODEL_PATH")
            or str(_DEFAULT_MODEL_DIR / _MODEL_FILENAME)
        )
        self._init_litert()

    # ── Initialisation ─────────────────────────────────────────────────────

    def _init_litert(self) -> None:
        try:
            from mediapipe.tasks.python.genai import llm_inference as llm  # type: ignore[import]
        except ImportError:
            logger.warning(
                "MediaPipe not installed. "
                "Run: pip install 'mediapipe>=0.10.21'"
            )
            return

        model_file = Path(self._model_path)
        if not model_file.exists():
            logger.error(
                "USE_LITERT=true but model file not found at %s. "
                "All responses will be placeholder text. "
                "Download from https://www.kaggle.com/models/google/gemma-4/litert/ "
                "and place at %s, or set GEMMA_MODEL_PATH to the correct path.",
                self._model_path,
                _DEFAULT_MODEL_DIR / _MODEL_FILENAME,
            )
            return

        try:
            options = llm.LlmInferenceOptions(
                model_path=str(model_file),
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                top_k=40,
            )
            self._model = llm.LlmInference.create_from_options(options)
            logger.info("Gemma 4 LiteRT model loaded: %s", self._model_path)
        except Exception as exc:
            logger.error("Failed to load Gemma 4 model: %s", exc)
            self._model = None

    # ── AIModelProvider interface ──────────────────────────────────────────

    @property
    def name(self) -> str:
        if self._model:
            return "Gemma 4 1B (LiteRT — local)"
        return "Gemma 4 (placeholder — model not loaded)"

    def complete(self, prompt: str) -> str:
        if self._model:
            return self._complete_litert(prompt)
        return self._complete_placeholder(prompt)

    # ── Private helpers ────────────────────────────────────────────────────

    def _complete_litert(self, prompt: str) -> str:
        try:
            result = self._model.generate_response(prompt)
            return result.strip() if result else "No response generated."
        except Exception as exc:
            logger.error("LiteRT generation failed: %s", exc)
            return self._complete_placeholder(prompt)

    @staticmethod
    def _complete_placeholder(prompt: str) -> str:
        """Rule-based fallback used when the model file is not present."""
        p = prompt.lower()

        if any(w in p for w in ("water", "irrigat", "moisture")):
            return (
                "To optimise irrigation: monitor soil moisture and water when it "
                "drops below 30%. Drip irrigation reduces water waste significantly."
            )
        if any(w in p for w in ("disease", "pest", "health", "sick")):
            return (
                "For disease and pest management:\n"
                "1. Scout fields regularly for early symptoms\n"
                "2. Apply targeted treatments promptly\n"
                "3. Use crop rotation to break pest cycles"
            )
        if any(w in p for w in ("plant", "crop", "sow", "seed")):
            return (
                "When planning planting, consider soil temperature, weather forecast, "
                "soil preparation, and pest history. What crop are you considering?"
            )
        if any(w in p for w in ("task", "todo", "work")):
            return (
                "Prioritise tasks by urgency and seasonal deadlines. "
                "Overdue items should be addressed first."
            )

        return (
            "I'm your AI farm advisor. I can help with irrigation, crop diseases, "
            "pests, planting, fertilisation, and task planning."
        )
