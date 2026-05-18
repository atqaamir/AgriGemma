"""
ChatbotService — Gemma 4 optimized orchestration.

Pipeline per message:
  1. Intent classification  — keyword-weighted, < 1 ms, no AI call
  2. Context building       — intent-aware fetch (only what this question needs)
  3. Context formatting     — compact labelled sections via components.py
  4. Prompt composition     — system + data + history + question
  5. AI call                — streaming or blocking
  6. Persist + return

Key improvements over previous version:
  - IntentClassifier replaces naive keyword-set detection
  - context_builder.build_chatbot_context() replaces full ContextAggregationService dump
  - components.py renders context as compact labelled text (not JSON blobs)
  - History limited to 3 messages (2 turns) — shorter = better for Gemma
  - BUDGET_CHATBOT_CONTEXT enforced at format time
  - Weather cache (120 s) prevents redundant API calls across messages
  - _format_farmer_context() is now pure formatting (no DB calls inside)
"""

import json
import logging
import queue as _queue
import re
import threading
import time
from datetime import datetime, timezone

from flask import current_app

from app.services.ai_model_service import ai_model_service
from app.services.intelligence_service.chatbot_service.prompts._prompt_chatbot_service import (
    build_chatbot_prompt,
)
from app.services.intelligence_service.intent.intent_classifier import (
    FarmIntent,
    IntentResult,
    classify,
)
from app.services.intelligence_service.context.context_builder import build_chatbot_context
from app.services.intelligence_service.context.token_budget import (
    BUDGET_CHATBOT_CONTEXT,
    BUDGET_CHATBOT_HISTORY,
    truncate,
)
from app.services.intelligence_service.prompts.components import (
    weather_block,
    weather_signals,
    field_block,
    crop_block,
    task_block,
    alert_block,
    rules_block,
    climate_block,
)
from app.repositories.chat_repository import ChatRepository
from app.services import web_search_service

logger = logging.getLogger(__name__)

# ── LLM output parser ──────────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> dict:
    text = re.sub(r'(?i)^\s*output\s*:\s*', '', raw.strip()).strip()

    def _get(key: str) -> str:
        # Strategy 1: quoted value where the closing quote is followed by , KEY: or }
        # The lookahead (?=\s*,\s*[A-Z_]{2,}\s*:|\s*[}]) prevents apostrophes in
        # contractions like "let's" from being mistaken for the closing quote.
        m = re.search(
            rf"{key}\s*:\s*([\"'])(.*?)\1(?=\s*,\s*[A-Z_]{{2,}}\s*:|\s*[}}])",
            text, re.IGNORECASE | re.DOTALL,
        )
        if m:
            return re.sub(r'\\(.)', r'\1', m.group(2).strip())
        # Strategy 2: unquoted value — stop at the next KEY: boundary or closing brace
        m = re.search(
            rf'{key}\s*:\s*(.*?)(?=,\s*[A-Z_]{{2,}}\s*:|[}}]|\Z)',
            text, re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip().strip("\"'")
        return ""

    # ── RESPONSE ──────────────────────────────────────────────────────────────
    response_raw = _get("RESPONSE")
    response = response_raw if response_raw else raw.strip()

    # ── URGENCY ───────────────────────────────────────────────────────────────
    raw_urgency = _get("URGENCY").lower()
    urgency = raw_urgency if raw_urgency in ("low", "medium", "high") else "medium"

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    raw_actions = _get("ACTIONS")
    actions = (
        [x.strip().strip("\"'") for x in raw_actions.split("|")
         if x.strip().strip("\"'").upper() not in ("", "NONE")]
        if raw_actions else []
    )

    return {"response": response, "urgency": urgency, "actions": actions}


# ── History helpers ────────────────────────────────────────────────────────────
_MAX_HISTORY_MESSAGES = 3   # last exchange (bot reply) + one prior user turn


def _build_history(messages: list) -> str:
    """
    Compress recent conversation into a compact history block.
    Limits to _MAX_HISTORY_MESSAGES and enforces BUDGET_CHATBOT_HISTORY.
    """
    recent = messages[-_MAX_HISTORY_MESSAGES:] if messages else []
    raw = "\n".join(
        f"{m.sender.upper()}: {m.message}"
        for m in recent
    )
    return truncate(raw, BUDGET_CHATBOT_HISTORY)


# ── Context formatting ─────────────────────────────────────────────────────────

def _format_farmer_context(
    context: dict,
    user_message: str,
    intent_result: IntentResult,
) -> str:
    """
    Render the intent-aware context dict into a compact string for the prompt.
    Uses components.py for all block rendering.
    Enforces BUDGET_CHATBOT_CONTEXT.
    """
    farmer_name = context.get("farmer_name") or "Farmer"
    weather     = context.get("weather") or {}
    fields      = context.get("fields") or []
    crops       = context.get("crops") or []
    tasks_ctx   = context.get("tasks") or {}
    alerts      = context.get("alerts") or []
    rules       = context.get("rules") or ""
    climate     = context.get("climate") or {}

    parts = [f"Farmer: {farmer_name}"]

    # Weather signals first — highest priority for Gemma
    wx_signals = weather_signals(weather, fields)
    if wx_signals:
        parts.append(wx_signals)

    # Weather block
    wx = weather_block(weather, days=3)
    if wx:
        parts.append(wx)

    # Fields (only when intent requested them)
    if fields:
        parts.append(field_block(fields))

    # Crops (usually present — lightweight)
    if crops:
        parts.append(crop_block(crops))

    # Tasks
    if tasks_ctx and tasks_ctx.get("pending_list"):
        pending = tasks_ctx["pending_list"]

        # If the user explicitly mentions a priority level, float those tasks to
        # the front so they survive the limit cut (default sort puts low last).
        _PRIORITY_HINTS = {
            "low":      ("low priority", "low-priority", "low tasks", "low ones", "low prio"),
            "medium":   ("medium priority", "medium-priority", "moderate priority"),
            "high":     ("high priority", "high-priority"),
            "critical": ("critical priority", "critical tasks", "critical ones", "critical"),
        }
        msg_lower = user_message.lower()
        mentioned = next(
            (p for p, kws in _PRIORITY_HINTS.items() if any(k in msg_lower for k in kws)),
            None,
        )
        if mentioned:
            focused = [t for t in pending if (t.get("priority") or "").lower() == mentioned]
            others  = [t for t in pending if (t.get("priority") or "").lower() != mentioned]
            tasks_ctx = {**tasks_ctx, "pending_list": focused + others}

        task_limit = len(tasks_ctx["pending_list"]) if intent_result.primary == FarmIntent.TASK else 6
        parts.append(task_block(tasks_ctx, limit=task_limit))

    # Alerts
    if alerts:
        parts.append(alert_block(alerts))

    # Rules (capped — already compact from RulesContextService)
    if rules:
        parts.append(rules_block(rules, 420))

    # Climate slice (only when intent explicitly needs it)
    if climate and intent_result.has(FarmIntent.WEATHER):
        blk = climate_block(climate, user_message)
        if blk:
            parts.append(blk)

    result = "\n\n".join(p for p in parts if p)
    budget = 4_000 if intent_result.primary in (FarmIntent.TASK, FarmIntent.GENERAL) else BUDGET_CHATBOT_CONTEXT
    return truncate(result, budget)


# ── Streaming response extractor ───────────────────────────────────────────────

class _ResponseStreamer:
    """
    Extracts the RESPONSE field from structured LLM output as tokens stream in.
    Yields partial chunks so the UI can show text progressively instead of
    waiting for the full generation to complete.

    Expected format: {RESPONSE: '...answer...', URGENCY: '...', ACTIONS: '...'}
    """
    _SAFETY = 14  # hold back this many chars to avoid splitting the end-marker

    def __init__(self):
        self._buf = ""
        self._found = False
        self._done = False
        self._quote = ""
        self._content_start = 0
        self._emitted = 0

    def feed(self, token: str) -> str:
        """Feed a raw LLM token; returns newly extractable response text (may be empty)."""
        if self._done:
            self._buf += token
            return ""
        self._buf += token
        if not self._found:
            m = re.search(r'RESPONSE\s*:\s*(["\'])', self._buf, re.IGNORECASE)
            if not m:
                return ""
            self._found = True
            self._quote = m.group(1)
            self._content_start = m.end()
        content = self._buf[self._content_start:]
        # Use ', URGENCY' as end-marker to avoid false positives on commas in the answer
        m_end = re.search(
            rf'{re.escape(self._quote)}\s*,\s*URGENCY', content, re.IGNORECASE
        )
        if m_end:
            chunk = content[self._emitted:m_end.start()]
            self._emitted = m_end.start()
            self._done = True
            return chunk
        safe_len = max(0, len(content) - self._SAFETY)
        chunk = content[self._emitted:safe_len]
        self._emitted = safe_len
        return chunk


# ── Main service ───────────────────────────────────────────────────────────────

class ChatbotService:
    """
    Smart agricultural chatbot — intent-first, context-selective, Gemma-optimized.
    """

    @staticmethod
    def get_or_create_conversation(user_id: int, conversation_id: int = None) -> int:
        if conversation_id:
            conversation = ChatRepository.get_conversation(conversation_id)
            if conversation and conversation.user_id == user_id:
                return conversation.id
        conversation = ChatRepository.create_conversation(
            user_id=user_id,
            title="Farm Chat",
            context={},
        )
        return conversation.id

    @staticmethod
    def send_message(user_id: int, conversation_id: int, user_message: str, language: str = 'en') -> dict:
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")

        user_msg = ChatRepository.create_message(
            conversation_id=conversation_id,
            sender="user",
            message=user_message,
        )

        messages = ChatRepository.get_messages(conversation_id)
        history  = _build_history(messages[:-1])   # exclude the message we just stored

        t_start = time.time()

        # Stage 1 — intent
        t1 = time.time()
        intent_result = classify(user_message)
        logger.info("[CHATBOT] ① Intent (%s, %dms): primary=%s secondary=%s conf=%.2f",
                    intent_result.method,
                    (time.time() - t1) * 1000,
                    intent_result.primary.value,
                    [i.value for i in intent_result.secondary],
                    intent_result.confidence)

        # Stage 2 — context (intent-aware fetch)
        t2 = time.time()
        context = build_chatbot_context(user_id, intent_result)
        context_str = _format_farmer_context(context, user_message, intent_result)
        logger.info("[CHATBOT] ② Context (%dms) — %d chars, intent=%s",
                    (time.time() - t2) * 1000, len(context_str), intent_result.primary.value)

        # Stage 2b — web search (GENERAL intent only)
        web_results = []
        if intent_result.primary == FarmIntent.GENERAL:
            web_results = web_search_service.search(user_message)

        # Stage 3 — AI
        full_prompt = build_chatbot_prompt(
            farmer_context=context_str,
            history=history,
            user_message=user_message,
            language=language,
            intent=intent_result.primary.value,
            web_results=web_results,
        )

        t3 = time.time()
        parsed   = {}
        is_fallback = False
        try:
            raw_llm = ai_model_service.complete(full_prompt)
            logger.info("[CHATBOT] ③ LLM raw output:\n%s", raw_llm)
            parsed      = _parse_llm_response(raw_llm)
            bot_response = parsed["response"]
            logger.info("[CHATBOT] ③ AI (%dms)", (time.time() - t3) * 1000)
        except Exception as exc:
            logger.warning("[CHATBOT] ③ AI failed (%dms): %s", (time.time() - t3) * 1000, exc)
            bot_response = ChatbotService._build_fallback_response(user_message, context)
            is_fallback  = True

        logger.info("[CHATBOT] ✓ Total: %dms", (time.time() - t_start) * 1000)

        bot_msg = ChatRepository.create_message(
            conversation_id=conversation_id,
            sender="bot",
            message=bot_response,
            metadata={
                "is_fallback": is_fallback,
                "model":       "fallback" if is_fallback else ai_model_service.get_provider().name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "urgency":     parsed.get("urgency", "medium"),
                "actions":     parsed.get("actions", []),
            },
        )

        if len(messages) == 1:
            ChatRepository.update_conversation_title(
                conversation_id, ChatbotService._generate_title(user_message)
            )

        return {
            "conversation_id":  conversation_id,
            "user_message_id":  user_msg.id,
            "bot_message_id":   bot_msg.id,
            "user_message":     user_msg.message,
            "bot_message":      bot_msg.message,
            "timestamp":        bot_msg.created_at.isoformat(),
            "metadata":         bot_msg.metadata_,
        }

    @staticmethod
    def get_conversation_messages(conversation_id: int, user_id: int) -> list:
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")
        return [
            {
                "id":        msg.id,
                "sender":    msg.sender,
                "message":   msg.message,
                "timestamp": msg.created_at.isoformat(),
                "metadata":  msg.metadata_,
            }
            for msg in ChatRepository.get_messages(conversation_id)
        ]

    @staticmethod
    def get_conversations(user_id: int, limit: int = 10) -> list:
        conversations = ChatRepository.get_user_conversations(user_id, limit)
        return [
            {
                "id":            conv.id,
                "title":         conv.title or "Farm Chat",
                "created_at":    conv.created_at.isoformat(),
                "updated_at":    conv.updated_at.isoformat(),
                "message_count": len(conv.messages),
            }
            for conv in conversations
        ]

    @staticmethod
    def delete_conversation(conversation_id: int, user_id: int) -> bool:
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")
        return ChatRepository.delete_conversation(conversation_id)

    @staticmethod
    def send_message_stream(user_id: int, conversation_id: int, user_message: str, language: str = 'en'):
        """
        Generator yielding SSE events for each pipeline stage.

        The pipeline runs in a non-daemon background thread so that navigating
        away mid-response does not abort the AI call — the bot message is always
        saved to the database even if the client disconnects.  The SSE generator
        simply reads from a queue; when the client drops (GeneratorExit) we stop
        reading while the thread finishes independently.
        """
        event_q: _queue.Queue = _queue.Queue()
        # Capture the app while we're still inside the request context;
        # the background thread has no app context of its own.
        app = current_app._get_current_object()

        def _worker():
            with app.app_context():
                try:
                    for chunk in ChatbotService._stream_pipeline(user_id, conversation_id, user_message, language):
                        event_q.put(chunk)
                except Exception as exc:
                    logger.error("[CHATBOT-STREAM] Worker error: %s", exc, exc_info=True)
                    event_q.put(
                        f'event: error\ndata: {json.dumps({"message": "Something went wrong."})}\n\n'
                    )
                finally:
                    event_q.put(None)  # sentinel — signals end of stream

        # daemon=False: thread outlives the request so the bot message is always saved
        threading.Thread(target=_worker, daemon=False).start()

        try:
            while True:
                try:
                    chunk = event_q.get(timeout=0.5)
                except _queue.Empty:
                    continue
                if chunk is None:
                    break
                yield chunk
        except GeneratorExit:
            # Client navigated away — background thread still completes and saves to DB
            pass

    @staticmethod
    def _stream_pipeline(user_id: int, conversation_id: int, user_message: str, language: str = 'en'):
        """
        Full streaming pipeline — runs inside a background thread.
        Yields SSE-formatted strings; always saves the bot message to DB before returning.
        """
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        t_start    = time.time()
        context    = {}
        user_msg   = None
        stages_log: list = []
        elapsed1 = elapsed2 = elapsed3 = 0

        def ms() -> int:
            return round((time.time() - t_start) * 1000)

        def stage_sse(stage: str, message: str, extra: dict | None = None) -> str:
            entry: dict = {"stage": stage, "label": message, "elapsed_ms": ms()}
            stages_log.append(entry)
            data: dict = {"stage": stage, "message": message, "stages_log": list(stages_log)}
            if extra:
                data.update(extra)
            return sse("status", data)

        try:
            conversation = ChatRepository.get_conversation(conversation_id)
            if not conversation or conversation.user_id != user_id:
                yield sse("error", {"message": "Invalid conversation"})
                return

            user_msg = ChatRepository.create_message(
                conversation_id=conversation_id, sender="user", message=user_message,
            )
            messages = ChatRepository.get_messages(conversation_id)
            history  = _build_history(messages[:-1])

            # ── Stage 1: intent ───────────────────────────────────────────────
            yield stage_sse("analyzing", "Analysing your question...")
            t1 = time.time()
            intent_result = classify(user_message)
            elapsed1 = round((time.time() - t1) * 1000)
            logger.info("[CHATBOT-STREAM] ① Intent (%dms): primary=%s secondary=%s",
                        elapsed1, intent_result.primary.value,
                        [i.value for i in intent_result.secondary])
            yield stage_sse(
                "intent_done",
                f"Intent: {intent_result.primary.value} — {elapsed1}ms",
                {
                    "intents":  [intent_result.primary.value] + [i.value for i in intent_result.secondary],
                    "method":   intent_result.method,
                    "time_ms":  elapsed1,
                },
            )

            # ── Stage 2: context ──────────────────────────────────────────────
            yield stage_sse("fetching_context", "Reading farm data...")
            t2 = time.time()
            context     = build_chatbot_context(user_id, intent_result)
            context_str = _format_farmer_context(context, user_message, intent_result)
            elapsed2    = round((time.time() - t2) * 1000)
            logger.info("[CHATBOT-STREAM] ② Context (%dms) %d chars", elapsed2, len(context_str))
            yield stage_sse(
                "context_ready",
                f"Farm context ready — {elapsed2}ms, {len(context_str)} chars",
                {"chars": len(context_str), "time_ms": elapsed2},
            )

            # ── Greeting fast-path (no LLM needed) ───────────────────────────
            if intent_result.primary == FarmIntent.GREETING:
                farmer_name = context.get("farmer_name") or "there"
                bot_response = (
                    f"Hi {farmer_name}! I'm AgriGemma, your AI farm advisor. "
                    "Ask me anything about your crops, irrigation, weather, tasks, or field health."
                )
                bot_msg = ChatRepository.create_message(
                    conversation_id=conversation_id,
                    sender="bot",
                    message=bot_response,
                    metadata={
                        "is_fallback": False,
                        "model": "greeting-fastpath",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "urgency": "low",
                        "actions": [],
                    },
                )
                if len(messages) == 1:
                    ChatRepository.update_conversation_title(
                        conversation_id, ChatbotService._generate_title(user_message)
                    )
                yield sse("token", {"text": bot_response})
                yield sse("response", {
                    "conversation_id": conversation_id,
                    "user_message_id": user_msg.id,
                    "bot_message_id":  bot_msg.id,
                    "user_message":    user_msg.message,
                    "bot_message":     bot_msg.message,
                    "timestamp":       bot_msg.created_at.isoformat(),
                    "metadata":        bot_msg.metadata_,
                    "total_ms":        ms(),
                    "stages_log":      stages_log,
                })
                return

            # ── Stage 2b: web search (GENERAL intent only) ────────────────────
            web_results = []
            if intent_result.primary == FarmIntent.GENERAL:
                yield stage_sse("searching_web", "Searching the web...")
                tw = time.time()
                web_results = web_search_service.search(user_message)
                elapsed_web = round((time.time() - tw) * 1000)
                logger.info("[CHATBOT-STREAM] ② Web search (%dms) %d results", elapsed_web, len(web_results))
                yield stage_sse(
                    "web_ready",
                    f"Found {len(web_results)} web results — {elapsed_web}ms",
                    {"result_count": len(web_results), "time_ms": elapsed_web},
                )

            full_prompt = build_chatbot_prompt(
                farmer_context=context_str,
                history=history,
                user_message=user_message,
                language=language,
                intent=intent_result.primary.value,
                web_results=web_results,
            )

            # ── Stage 3: AI streaming ─────────────────────────────────────────
            yield stage_sse("generating", f"Generating response... (pipeline ready in {ms()}ms)")
            t3 = time.time()
            bot_response = ""
            is_fallback  = False
            parsed       = {}
            try:
                streamer    = _ResponseStreamer()
                raw_tokens  = []
                accumulated = ""
                for token in ai_model_service.stream_complete(full_prompt):
                    raw_tokens.append(token)
                    chunk = streamer.feed(token)
                    if chunk:
                        accumulated += chunk
                        yield sse("token", {"text": accumulated})
                raw_llm = "".join(raw_tokens)
                logger.info("[CHATBOT-STREAM] ③ LLM raw output:\n%s", raw_llm)
                parsed       = _parse_llm_response(raw_llm)
                bot_response = parsed["response"]
                elapsed3     = round((time.time() - t3) * 1000)
                logger.info("[CHATBOT-STREAM] ③ AI (%dms) %d chars", elapsed3, len(bot_response))
                yield sse("token", {"text": bot_response})
            except Exception as exc:
                elapsed3 = round((time.time() - t3) * 1000)
                logger.warning("[CHATBOT-STREAM] ③ AI failed (%dms): %s", elapsed3, exc)
                if not bot_response:
                    bot_response = ChatbotService._build_fallback_response(user_message, context)
                    is_fallback  = True
                    yield sse("token", {"text": bot_response})

            total_ms = ms()
            logger.info(
                "[CHATBOT-STREAM] ✓ Total: %dms  (intent=%dms  context=%dms  ai=%dms)",
                total_ms, elapsed1, elapsed2, elapsed3,
            )

            bot_msg = ChatRepository.create_message(
                conversation_id=conversation_id,
                sender="bot",
                message=bot_response,
                metadata={
                    "is_fallback":  is_fallback,
                    "model":        "fallback" if is_fallback else ai_model_service.get_provider().name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_ms":     total_ms,
                    "stage_ms":     {"intent": elapsed1, "context": elapsed2, "ai": elapsed3},
                    "urgency":      parsed.get("urgency", "medium"),
                    "actions":      parsed.get("actions", []),
                },
            )

            if len(messages) == 1:
                ChatRepository.update_conversation_title(
                    conversation_id, ChatbotService._generate_title(user_message)
                )

            yield sse("response", {
                "conversation_id": conversation_id,
                "user_message_id": user_msg.id,
                "bot_message_id":  bot_msg.id,
                "user_message":    user_msg.message,
                "bot_message":     bot_msg.message,
                "timestamp":       bot_msg.created_at.isoformat(),
                "metadata":        bot_msg.metadata_,
                "total_ms":        total_ms,
                "stages_log":      stages_log,
            })

        except Exception as exc:
            total_ms = ms()
            logger.error("[CHATBOT-STREAM] Unhandled error after %dms: %s", total_ms, exc, exc_info=True)
            yield sse("error", {"message": "Something went wrong. Please try again."})

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _generate_title(first_message: str) -> str:
        return first_message[:47] + "..." if len(first_message) > 50 else first_message

    @staticmethod
    def _build_fallback_response(user_message: str, context: dict) -> str:
        """Rule-based response when AI is unavailable. Uses intent context."""
        m      = user_message.lower()
        fields = context.get("fields") or []
        tasks  = context.get("tasks") or {}
        crops  = context.get("crops") or []
        farmer = context.get("farmer_name") or "there"

        # Irrigation
        if any(w in m for w in ("water", "irrigat", "moisture", "dry")):
            dry_fields = [f for f in fields if (f.get("moisture_level") or 100) < 30]
            if dry_fields:
                f = dry_fields[0]
                return (
                    f"{farmer}, {f['name']} has critically low soil moisture "
                    f"({f.get('moisture_level', '?')}%). Irrigate that field today — "
                    "moisture below 30% causes crop stress and reduced yield."
                )
            return (
                f"{farmer}, monitor soil moisture and irrigate when it drops below 30%. "
                "Check your scheduled irrigation tasks for timing details."
            )

        # Disease / pest
        if any(w in m for w in ("disease", "sick", "pest", "insect", "fungus")):
            sick = [f for f in fields if (f.get("health_status") or "").lower() in ("poor", "alert", "critical")]
            if sick:
                return (
                    f"{farmer}, {sick[0]['name']} shows {sick[0]['health_status']} health status. "
                    "Scout that field today for visible symptoms. "
                    "Early detection prevents spread to other fields."
                )
            return (
                f"{farmer}, scout your fields regularly. Look for yellowing, spots, or unusual wilting. "
                "If you see symptoms, note the affected area and crop stage before applying treatment."
            )

        # Tasks
        if any(w in m for w in ("task", "todo", "what should", "urgent", "overdue")):
            pending = tasks.get("pending_count") or 0
            overdue = tasks.get("overdue_count") or 0
            if overdue:
                return (
                    f"{farmer}, you have {overdue} overdue task(s) that need immediate attention. "
                    f"Open your task list and address those first before they impact your crops."
                )
            return (
                f"{farmer}, you have {pending} pending tasks. "
                "Start with the highest-priority ones and check if any are approaching their due date."
            )

        # Weather
        if any(w in m for w in ("weather", "rain", "heat", "temperature", "forecast")):
            weather = context.get("weather") or {}
            current = (weather.get("current") or {})
            temp = current.get("temp") or current.get("temperature_c") or "?"
            if weather.get("heatwave_risk"):
                return (
                    f"{farmer}, there is an active heatwave risk ({temp}°C). "
                    "Increase irrigation frequency and avoid fertilizing during peak heat hours."
                )
            if weather.get("rain_expected"):
                return (
                    f"{farmer}, rain is expected soon. "
                    "Hold off on irrigation and delay any pending soil work until after rainfall."
                )
            return (
                f"{farmer}, current temperature is {temp}°C. "
                "Keep monitoring the forecast and adjust irrigation and field work accordingly."
            )

        # Planting / harvest
        if any(w in m for w in ("plant", "sow", "harvest", "ripen", "ready")):
            crop_names = ", ".join(c.get("name", "?") for c in crops[:3])
            if crop_names:
                return (
                    f"{farmer}, your active crops are {crop_names}. "
                    "Check your seasonal plan for sowing and harvest windows, "
                    "and make sure soil preparation is complete before planting."
                )
            return (
                f"{farmer}, choose crops suited to your soil type and current season. "
                "Check the seasonal calendar for optimal sowing windows in your region."
            )

        return (
            f"{farmer}, I'm here to help with irrigation, crop health, weather, pests, "
            "fertilization, and task management. What would you like to know?"
        )
