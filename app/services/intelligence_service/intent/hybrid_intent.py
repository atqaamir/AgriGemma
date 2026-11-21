"""Hybrid intent: keywords first; the AI only when no keyword matched or the keyword
result is uncertain.

classify_hybrid(message) -> IntentResult
  1. intent_classifier.classify (keywords, < 1 ms). A match with confidence >= LOW_CONFIDENCE,
     a greeting or an explicit general question / short follow-up is returned as is.
  2. Otherwise one complete_intent call on the fast provider (the 10 labels, temperature 0,
     minimal thinking) with a LIMIT_S deadline. A valid label → that intent (method "ai");
     an invalid label, an error, a timeout or no AI provider → GENERAL (method "ai-failed").
No embeddings. The result records whether the AI ran and how long it took (stats()).
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
from dataclasses import replace

from app.services.intelligence_service.intent.intent_classifier import FarmIntent, IntentResult, classify

logger = logging.getLogger(__name__)

LOW_CONFIDENCE = 0.5     # keyword results below this are uncertain (the lowest eval question: 0.55)
LIMIT_S = 3.0
LABELS = tuple(i.value for i in FarmIntent)
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="intent")
_stats = {"calls": 0, "ai_ok": 0, "ai_failed": 0, "ms": []}


def needs_ai(r: IntentResult) -> bool:
    if r.primary == FarmIntent.GREETING:
        return False
    if r.primary == FarmIntent.GENERAL:
        return r.confidence == 0.0                       # nothing matched
    return r.confidence < LOW_CONFIDENCE


def _ask_ai(message: str) -> str | None:
    """The fast provider's complete_intent (replaced in tests). None without one."""
    from app.services.ai_model_service import ai_model_service
    provider = ai_model_service._fast_provider or ai_model_service.get_provider()
    if not hasattr(provider, "complete_intent"):
        return None
    return provider.complete_intent(message, LABELS, timeout=LIMIT_S)


def classify_hybrid(message: str) -> IntentResult:
    r = classify(message)
    if not needs_ai(r):
        return r
    t0 = time.monotonic()
    _stats["calls"] += 1
    try:
        label = _pool.submit(_ask_ai, message).result(timeout=LIMIT_S + 0.2)
    except _Timeout:
        label = None
        logger.warning("Intent AI: no answer within %.1f s - GENERAL", LIMIT_S)
    except Exception as exc:
        label = None
        logger.warning("Intent AI failed (%s) - GENERAL", exc)
    ms = round((time.monotonic() - t0) * 1000)
    _stats["ms"].append(ms)
    label = (label or "").strip().lower()
    if label in LABELS:
        _stats["ai_ok"] += 1
        logger.info("Intent AI (%d ms): %r -> %s (keywords: %s %.2f)", ms, message[:60], label,
                    r.primary.value, r.confidence)
        return IntentResult(primary=FarmIntent(label), secondary=[], confidence=r.confidence, method="ai")
    _stats["ai_failed"] += 1
    logger.info("Intent AI (%d ms): %r -> no valid label (%r) - GENERAL", ms, message[:60], label[:20])
    return replace(r, primary=FarmIntent.GENERAL, secondary=[], method="ai-failed")


def stats() -> dict:
    return {k: (list(v) if isinstance(v, list) else v) for k, v in _stats.items()}


def reset_stats() -> None:
    _stats.update(calls=0, ai_ok=0, ai_failed=0, ms=[])
