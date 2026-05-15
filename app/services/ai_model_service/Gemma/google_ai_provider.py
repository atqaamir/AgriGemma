"""
Google AI Studio provider — Gemma 4 cloud inference for the chatbot.

Used ONLY for the real-time chatbot (streaming responses to farmer questions).
All background intelligence tasks (task/notification explanations, summaries) run
on local Ollama Gemma 4 to enable offline/low-connectivity operation.

Setup
-----
1. Go to https://aistudio.google.com/apikey and create a free API key.
2. Set environment variables:
       GOOGLE_API_KEY=your_key_here
       USE_GOOGLE_AI=true
       GOOGLE_AI_MODEL=gemma-4-26b-a4b-it   (optional — default shown)

Kaggle Gemma 4 Good Hackathon — available Google AI Studio model IDs:
    gemma-4-26b-a4b-it   MoE: 4B active / 26B total, 256K context  ← default (efficient)
    gemma-4-31b-it       31B dense, 256K context                    (highest quality)

Streaming
---------
Uses Google's SSE streaming endpoint so tokens appear immediately in the chatbot UI.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Iterator

from app.services.ai_model_service.ai_provider_interface import AIModelProvider

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"
_DEFAULT_MODEL = "gemma-4-26b-a4b-it"   # MoE: 4B active params, cost-efficient for streaming
_SYSTEM_SEP = "\x00SYS\x00"  # must match _prompt_chatbot_service.py

def _strip_preamble(text: str) -> str:
    """
    If the model emitted inline thinking before the structured block, discard it.
    Finds the first occurrence of RESPONSE: and returns from there.
    Falls back to _extract_clean_response when RESPONSE: never appears.
    """
    idx = text.find("RESPONSE:")
    if idx > 0:
        return text[idx:]
    if idx == -1:
        return _extract_clean_response(text)
    return text


def _extract_clean_response(text: str) -> str:
    """
    Gemma 4 can leak chain-of-thought as plain text even when told not to.
    Strategy 1: extract content from "* Sentence N: ..." draft format.
    Strategy 2: pull the last double-quoted block (model's own final draft).
    Fallback: strip bullet/analytical lines and return last real paragraph.
    """
    import re

    # Strategy 1: model outputs "* Sentence 1: ...\n* Sentence 2: ...\n* Check: ..."
    # Extract only the sentence content, discard self-check lines.
    sentence_lines = re.findall(r'^\*\s+Sentence\s+\d+:\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
    if sentence_lines:
        return " ".join(s.strip() for s in sentence_lines).strip()

    # Strategy 2: model wraps final draft in double quotes — take the last one
    quoted = re.findall(r'"([^"]{30,})"', text)
    if quoted:
        return quoted[-1].strip()

    # Fallback: strip thinking-style lines and prompt echoes
    _SKIP_PREFIXES = ("* ", "- ", "? ", "Wait,", "Let", "Check", "This is", "That", "Everything",
                      "I should", "I'll", "I will", "I would", "One more", "Let me", "Sentence",
                      "Here is", "Here's", "Based on", "Sure,", "Sure!", "Okay,", "Okay!", "Use ")
    _SKIP_PATTERNS = (
        r"^\? \(",
        r".*\? (Yes|No)\.?$",
        r"^- Use .+\?",
    )

    clean = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in _SKIP_PREFIXES):
            continue
        if any(re.match(pattern, s) for pattern in _SKIP_PATTERNS):
            continue
        if s and s[0].isdigit() and len(s) > 1 and s[1] in ".):":
            continue
        clean.append(s)
    return " ".join(clean).strip() or text


class GoogleAIProvider(AIModelProvider):
    """Gemma via Google AI Studio REST API. No extra dependencies required."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._model   = model  or os.getenv("GOOGLE_AI_MODEL", _DEFAULT_MODEL)
        if not self._api_key:
            logger.warning(
                "GoogleAIProvider: GOOGLE_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        else:
            try:
                self._model = self._resolve_model(self._model)
            except Exception as exc:
                logger.warning("Google AI startup check failed: %s", exc)
            logger.info("Google AI provider ready — model: %s", self._model)

    def _resolve_model(self, requested: str) -> str:
        """Return `requested` if available, otherwise pick the best available Gemma model."""
        url = f"{_BASE}/models?key={self._api_key}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            logger.warning("Could not list models: %s", exc)
            return requested

        available = [
            m["name"].replace("models/", "")
            for m in data.get("models", [])
            if "gemma" in m.get("name", "").lower()
            and "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        logger.info("Available Gemma models: %s", ", ".join(available) if available else "none")

        if requested in available:
            return requested

        # Pick best available: prefer gemma-4, then gemma-3; prefer larger param counts
        def _rank(name: str) -> tuple:
            gen = 4 if "gemma-4" in name else (3 if "gemma-3" in name else 0)
            size = next((int(p) for p in name.split("-") if p.isdigit() and int(p) > 1), 0)
            return (gen, size)

        if available:
            best = max(available, key=_rank)
            logger.warning(
                "Configured model %r not available — using %r instead. "
                "Update GOOGLE_AI_MODEL in .env to silence this warning.",
                requested, best,
            )
            return best

        logger.warning("No Gemma models found — check your API key permissions")
        return requested

    @property
    def name(self) -> str:
        return f"Google AI/{self._model}"

    # ── Public interface ───────────────────────────────────────────────────

    def complete_intent(self, message: str, valid_intents: tuple[str, ...]) -> set[str]:
        """Lightweight AI call to classify a message into intent tags."""
        if not self._api_key:
            return set()
        intents_list = ", ".join(valid_intents)
        prompt = (
            f"Classify this farmer message into one or more of these intents: {intents_list}.\n"
            f"Message: \"{message}\"\n"
            f"Reply ONLY with a comma-separated list of matching intents. "
            f"If none match, reply with: general"
        )
        try:
            payload = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 40},
            }).encode("utf-8")
            url = f"{_BASE}/models/{self._model}:generateContent?key={self._api_key}"
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip().lower()
            detected = {t.strip() for t in text.split(",") if t.strip() in valid_intents}
            return detected or {"general"}
        except Exception as exc:
            logger.warning("Google AI intent detection failed: %s", exc)
            return set()

    def complete(self, prompt: str) -> str:
        if not self._api_key:
            logger.error("Google AI: GOOGLE_API_KEY not set — get one at https://aistudio.google.com/apikey")
            return self._placeholder(prompt)
        logger.debug("Google AI complete: %d chars", len(prompt))
        try:
            return self._call_api(prompt)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error("Google AI %s — model=%s — %s", exc, self._model, body)
            return self._placeholder(prompt)
        except Exception as exc:
            logger.error("Google AI inference failed: %s", exc)
            return self._placeholder(prompt)

    def stream_complete(self, prompt: str) -> Iterator[str]:
        if not self._api_key:
            logger.error("Google AI: GOOGLE_API_KEY not set — get one at https://aistudio.google.com/apikey")
            yield self._placeholder(prompt)
            return
        logger.debug("Google AI stream: %d chars", len(prompt))
        try:
            yield from self._stream_api(prompt)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.warning("Google AI streaming failed (HTTP %s) — body: %s", exc.code, body[:300])
            try:
                yield self._call_api(prompt)
            except urllib.error.HTTPError as exc2:
                body2 = exc2.read().decode("utf-8", errors="replace")
                logger.error("Google AI non-streaming fallback failed: HTTP %s — body: %s", exc2.code, body2[:300])
                yield self._placeholder(prompt)
            except Exception as exc2:
                logger.error("Google AI non-streaming fallback failed: %s", exc2)
                yield self._placeholder(prompt)
        except Exception as exc:
            logger.warning("Google AI streaming failed (%s) — falling back to non-streaming", exc)
            try:
                yield self._call_api(prompt)
            except Exception as exc2:
                logger.error("Google AI non-streaming fallback failed: %s", exc2)
                yield self._placeholder(prompt)

    # ── Private helpers ────────────────────────────────────────────────────

    _FEW_SHOT = [
        (
            "FARM DATA:\nFarmer: Ali\nWeather: 38°C, no rain for 5 days\n"
            "Crops: Wheat (North Field, moisture 22%)\n\n"
            "FARMER ASKS: should I water today?",
            "{RESPONSE: 'With 38°C heat and moisture down to 22%, the wheat in North Field needs water today — don't wait.', "
            "URGENCY: 'high', ACTIONS: 'Irrigate North Field today | Check moisture again tomorrow'}",
        ),
        (
            "FARM DATA:\nFarmer: Sara\nWeather: 24°C, rain expected tomorrow\n"
            "TASKS: 8 pending — [LOW] Fix fence (South Field, due 2026-05-20) | [LOW] Clean storage shed (due 2026-05-22) | [MEDIUM] Fertilize cotton (due 2026-05-18)\n\n"
            "FARMER ASKS: show me my low priority tasks",
            "{RESPONSE: 'You have 2 low priority tasks: Fix fence at South Field (due May 20) and Clean storage shed (due May 22).', "
            "URGENCY: 'low', ACTIONS: 'Fix fence South Field | Clean storage shed'}",
        ),
        (
            "FARM DATA:\nFarmer: Raza\nWeather: 29°C, humidity 80%, rain in 2 days\n"
            "Crops: Rice (East Field, stage: flowering)\n\n"
            "FARMER ASKS: is the weather good for my rice?",
            "{RESPONSE: 'The 80% humidity is fine for flowering rice, but hold off on any fertilizer or spraying — rain is coming in 2 days and will wash it off.', "
            "URGENCY: 'medium', ACTIONS: 'Delay fertilizer application | Monitor crop after rain'}",
        ),
    ]

    def _payload(self, prompt: str, *, max_tokens: int = 2048) -> bytes:
        if _SYSTEM_SEP in prompt:
            system_text, user_text = prompt.split(_SYSTEM_SEP, 1)
            system_text = system_text.strip()
            user_text = user_text.strip()
        else:
            system_text = None
            user_text = prompt

        contents = []
        for user_ex, model_ex in self._FEW_SHOT:
            contents.append({"role": "user",  "parts": [{"text": user_ex}]})
            contents.append({"role": "model", "parts": [{"text": model_ex}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        return json.dumps(payload).encode("utf-8")

    def _call_api(self, prompt: str, *, model: str | None = None) -> str:
        m = model or self._model
        url = f"{_BASE}/models/{m}:generateContent?key={self._api_key}"
        req = urllib.request.Request(
            url, data=self._payload(prompt),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip():
            text = "".join(p.get("text", "") for p in parts)
        text = text.strip()
        return _strip_preamble(text)

    def _stream_api(self, prompt: str, *, model: str | None = None) -> Iterator[str]:
        m = model or self._model
        url = (
            f"{_BASE}/models/{m}:streamGenerateContent"
            f"?key={self._api_key}&alt=sse"
        )
        req = urllib.request.Request(
            url, data=self._payload(prompt),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        thought_buf = []
        has_response = False

        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    obj = json.loads(data_str)
                    part = obj["candidates"][0]["content"]["parts"][0]
                    token = part.get("text", "")
                    if not token:
                        continue
                    if part.get("thought"):
                        thought_buf.append(token)
                    else:
                        has_response = True
                        yield token  # emit each token immediately as it arrives
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue

        # Only fall back to thought content if the model emitted no response tokens
        if not has_response and thought_buf:
            cleaned = _strip_preamble("".join(thought_buf))
            if cleaned:
                yield cleaned

    @staticmethod
    def _placeholder(prompt: str) -> str:
        return "The AI advisor is not available right now. Please try again in a moment."
