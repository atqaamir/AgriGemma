"""
Ollama local inference provider.

Works on Windows, Mac, and Linux. Requires Ollama running locally.

Setup
-----
1. Download and install Ollama: https://ollama.com/download
2. Pull a model:
       ollama pull gemma3:4b          (recommended — ~3 GB)
       ollama pull gemma3:1b          (faster, smaller — ~800 MB)
3. Ollama starts automatically in the background after install.

Environment variables
---------------------
OLLAMA_HOST    — Ollama base URL  (default: http://localhost:11434)
OLLAMA_MODEL   — Model name       (default: gemma3:4b)
"""

import logging
import urllib.request
import urllib.error
import json
import os

from app.services.ai_model_service.ai_provider_interface import AIModelProvider

logger = logging.getLogger(__name__)

_DEFAULT_HOST  = "http://localhost:11434"
_DEFAULT_MODEL = "gemma3:4b"


class OllamaProvider(AIModelProvider):
    """
    Runs any Ollama model (Gemma 3, Llama 3, Mistral, etc.) locally.
    Falls back to placeholder responses if Ollama is not reachable.
    """

    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self._host  = (host  or os.getenv("OLLAMA_HOST",  _DEFAULT_HOST)).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL", _DEFAULT_MODEL)
        self._available = self._check_availability()

    # ── Availability check ─────────────────────────────────────────────────

    def _check_availability(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            if self._model in models:
                logger.info("Ollama ready — model: %s", self._model)
                return True
            prefix = self._model.split(":")[0]
            variants = [m for m in models if m.startswith(prefix)]
            if variants:
                self._model = variants[0]
                logger.info(
                    "Ollama: requested model not found; using available variant: %s",
                    self._model,
                )
                return True
            logger.warning(
                "Ollama is running but model '%s' is not pulled. "
                "Run: ollama pull %s",
                self._model, self._model,
            )
            return False
        except urllib.error.URLError:
            logger.warning(
                "Ollama not reachable at %s. "
                "Download from https://ollama.com/download, then run: ollama pull %s",
                self._host, self._model,
            )
            return False
        except Exception as exc:
            logger.warning("Ollama availability check failed: %s", exc)
            return False

    # ── AIModelProvider interface ──────────────────────────────────────────

    @property
    def name(self) -> str:
        if self._available:
            return f"Ollama/{self._model} (local)"
        return f"Ollama/{self._model} (offline — placeholder)"

    def complete(self, prompt: str) -> str:
        if not self._available:
            return self._placeholder(prompt)
        try:
            return self._call_ollama(prompt)
        except Exception as exc:
            logger.error("Ollama inference failed: %s", exc)
            self._available = False
            return self._placeholder(prompt)

    # ── Private helpers ────────────────────────────────────────────────────

    def _call_ollama(self, prompt: str) -> str:
        payload = json.dumps({
            "model":  self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.95,
                "num_predict": 512,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        return (data.get("response") or "").strip()

    @staticmethod
    def _placeholder(prompt: str) -> str:
        p = prompt.lower()
        if any(w in p for w in ("water", "irrigat", "moisture")):
            return (
                "Monitor soil moisture and irrigate when it drops below 30%. "
                "Drip irrigation reduces water use by up to 50%."
            )
        if any(w in p for w in ("disease", "pest", "health", "sick")):
            return (
                "Scout fields regularly for early symptoms. Apply targeted treatments "
                "promptly and use crop rotation to break pest cycles."
            )
        if any(w in p for w in ("plant", "crop", "sow", "seed")):
            return (
                "Consider soil temperature, weather forecast, soil preparation, and pest "
                "history when planning planting. What crop are you considering?"
            )
        if any(w in p for w in ("task", "todo", "work")):
            return "Prioritise tasks by urgency and seasonal deadlines. Address overdue items first."
        return (
            "I'm your AI farm advisor. I can help with irrigation, crop diseases, "
            "pests, planting, fertilisation, and task planning."
        )
