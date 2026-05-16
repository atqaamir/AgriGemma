"""
Ollama local inference provider — Gemma 4 on-device.

Used for background intelligence tasks (task explanations, notification explanations,
dashboard/task summaries). Runs fully offline — no internet required after pulling
the model. This is what makes the system work in low-connectivity farm environments.

Setup
-----
1. Download and install Ollama: https://ollama.com/download
2. Pull Gemma 4:
       ollama pull gemma4            # default e4b — 9.6 GB, best quality/size balance
       ollama pull gemma4:e2b        # lighter — 7.2 GB, faster on low-RAM machines
       ollama pull gemma4:26b        # highest quality — 18 GB, needs 24 GB+ RAM
3. Ollama starts automatically in the background after install.

Environment variables
---------------------
OLLAMA_HOST    — Ollama base URL  (default: http://localhost:11434)
OLLAMA_MODEL   — Model name       (default: gemma4)

Kaggle Gemma 4 Good Hackathon — Gemma 4 model sizes:
    gemma4:e2b   2.3B effective params, 128K context, edge/mobile
    gemma4:e4b   4.5B effective params, 128K context, edge/laptop  ← default
    gemma4:26b   4B active / 26B total MoE,  256K context
    gemma4:31b   31B dense, 256K context, best quality
"""

import logging
import time
import urllib.request
import urllib.error
import json
import os
import socket

from app.services.ai_model_service.ai_provider_interface import AIModelProvider

logger = logging.getLogger(__name__)

_DEFAULT_HOST  = "http://localhost:11434"
_DEFAULT_MODEL = "gemma4"   # pulls e4b (9.6 GB) by default


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
        except (TimeoutError, socket.timeout) as exc:
            logger.error("Ollama inference timed out: %s", exc)
            return self._placeholder(prompt)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                logger.error("Ollama inference timed out: %s", exc)
                return self._placeholder(prompt)
            logger.error("Ollama inference failed: %s", exc)
            self._available = False
            return self._placeholder(prompt)
        except Exception as exc:
            logger.error("Ollama inference failed: %s", exc)
            self._available = False
            return self._placeholder(prompt)

    # ── Private helpers ────────────────────────────────────────────────────

    def stream_complete(self, prompt: str):
        if not self._available:
            yield self._placeholder(prompt)
            return
        try:
            yield from self._stream_ollama(prompt)
        except Exception as exc:
            logger.error("Ollama streaming failed: %s", exc)
            yield self._placeholder(prompt)

    @staticmethod
    def _split_prompt(prompt: str) -> tuple[str, str]:
        """Split a prompt encoded by build_chatbot_prompt into (system, user)."""
        _SEP = "\x00SYS\x00"
        if _SEP in prompt:
            system, _, user = prompt.partition(_SEP)
            return system.strip(), user.strip()
        return "", prompt

    def _stream_ollama(self, prompt: str):
        system, user = self._split_prompt(prompt)
        body: dict = {
            "model":  self._model,
            "prompt": user,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 512,
                "num_ctx": 8192,   # Gemma 4 supports up to 128K; 8K covers all intelligence prompts
            },
        }
        if system:
            body["system"] = system
        payload = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                token = obj.get("response", "")
                if token:
                    yield token
                if obj.get("done"):
                    break

    def complete_json(self, prompt: str) -> str:
        """Like complete() but asks Ollama for JSON-mode output.
        Use when the response must be a JSON object (e.g. dashboard intelligence).
        Returns empty string on timeout/failure so _parse_response raises and
        the caller falls back gracefully."""
        if not self._available:
            logger.warning("[ollama] complete_json skipped — provider offline (model=%s)", self._model)
            return ""
        logger.info(
            "[ollama] complete_json → model=%s | host=%s | prompt=%d chars | "
            "format=json | num_predict=1024 | num_ctx=8192 | timeout=120s",
            self._model, self._host, len(prompt),
        )
        try:
            result = self._call_ollama(prompt, json_mode=True)
            logger.info("[ollama] complete_json ← %d chars received", len(result))
            logger.debug("[ollama] complete_json response: %s", result[:500] if result else "<empty>")
            return result
        except (TimeoutError, socket.timeout) as exc:
            logger.error(
                "[ollama] complete_json TIMED OUT after 120s — model=%s. "
                "Consider using a smaller model (gemma4:e2b) or increasing timeout. Error: %s",
                self._model, exc,
            )
            return ""
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                logger.error(
                    "[ollama] complete_json TIMED OUT after 120s — model=%s. "
                    "Consider using a smaller model (gemma4:e2b) or increasing timeout. Error: %s",
                    self._model, exc,
                )
                return ""
            logger.error(
                "[ollama] complete_json CONNECTION FAILED — model=%s, host=%s. "
                "Is Ollama running? Error: %s",
                self._model, self._host, exc,
            )
            self._available = False
            return ""
        except Exception as exc:
            logger.error(
                "[ollama] complete_json UNEXPECTED ERROR — model=%s: %s",
                self._model, exc, exc_info=True,
            )
            self._available = False
            return ""

    def _call_ollama(self, prompt: str, json_mode: bool = False) -> str:
        system, user = self._split_prompt(prompt)
        num_predict = 1024 if json_mode else 800
        body: dict = {
            "model":  self._model,
            "prompt": user,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": num_predict,
                "num_ctx": 8192,
            },
        }
        if system:
            body["system"] = system
        if json_mode:
            body["format"] = "json"

        logger.debug(
            "[ollama] _call_ollama — model=%s | format=%s | num_predict=%d | "
            "system=%d chars | user=%d chars",
            self._model,
            body.get("format", "text"),
            num_predict,
            len(system),
            len(user),
        )

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        elapsed = time.monotonic() - t0

        response    = (data.get("response") or "").strip()
        done_reason = data.get("done_reason", "unknown")
        eval_count  = data.get("eval_count", "?")   # tokens generated

        logger.info(
            "[ollama] _call_ollama done — elapsed=%.1fs | tokens_out=%s | "
            "done_reason=%s | response=%d chars",
            elapsed, eval_count, done_reason, len(response),
        )
        if done_reason == "length":
            logger.warning(
                "[ollama] output truncated by num_predict=%d — JSON will likely be incomplete. "
                "Increase num_predict or shorten the prompt.",
                num_predict,
            )

        return response

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
