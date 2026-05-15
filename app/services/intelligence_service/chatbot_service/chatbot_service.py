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
import re
import time
from datetime import datetime, timezone

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

logger = logging.getLogger(__name__)

# ── LLM output parser ──────────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> dict:
    m = re.search(r'RESPONSE\s*:\s*(.+?)(?=\n\s*(?:URGENCY|ACTIONS)\s*:|\Z)', raw.strip(), re.DOTALL | re.IGNORECASE)
    response = m.group(1).strip() if m else raw.strip()

    u = re.search(r'URGENCY\s*:\s*(\w+)', raw, re.IGNORECASE)
    raw_urgency = u.group(1).lower() if u else ""
    urgency = raw_urgency if raw_urgency in ("low", "medium", "high") else "medium"

    a = re.search(r'ACTIONS\s*:\s*(.+?)(?=\n\s*[A-Z]{2,}\s*:|\Z)', raw, re.DOTALL | re.IGNORECASE)
    raw_actions = a.group(1).strip() if a else ""
    actions = [x.strip() for x in raw_actions.split("|") if x.strip() and x.strip().upper() != "NONE"] if raw_actions else []

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
        parts.append(task_block(tasks_ctx, limit=6))

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
    return truncate(result, BUDGET_CHATBOT_CONTEXT)


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
    def send_message(user_id: int, conversation_id: int, user_message: str) -> dict:
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

        # Stage 3 — AI
        full_prompt = build_chatbot_prompt(
            farmer_context=context_str,
            history=history,
            user_message=user_message,
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
    def send_message_stream(user_id: int, conversation_id: int, user_message: str):
        """
        Generator yielding SSE events for each pipeline stage.
        Format: "event: <type>\\ndata: <json>\\n\\n"
        """
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        t_start = time.time()
        context  = {}
        user_msg = None

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
            yield sse("status", {"stage": "analyzing", "message": "Analysing your question..."})
            t1 = time.time()
            intent_result = classify(user_message)
            elapsed1 = round((time.time() - t1) * 1000)
            logger.info("[CHATBOT-STREAM] ① Intent (%dms): primary=%s secondary=%s",
                        elapsed1, intent_result.primary.value,
                        [i.value for i in intent_result.secondary])
            yield sse("status", {
                "stage":    "intents_detected",
                "message":  f"Understood: {intent_result.primary.value}",
                "intents":  [intent_result.primary.value] + [i.value for i in intent_result.secondary],
                "method":   intent_result.method,
                "time_ms":  elapsed1,
            })

            # ── Stage 2: context ──────────────────────────────────────────────
            yield sse("status", {"stage": "reading_rules", "message": "Reading farm data..."})
            t2 = time.time()
            context     = build_chatbot_context(user_id, intent_result)
            context_str = _format_farmer_context(context, user_message, intent_result)
            elapsed2    = round((time.time() - t2) * 1000)
            logger.info("[CHATBOT-STREAM] ② Context (%dms) %d chars", elapsed2, len(context_str))
            yield sse("status", {
                "stage":    "context_ready",
                "message":  f"Farm context ready ({len(context_str)} chars)",
                "time_ms":  elapsed2,
            })

            full_prompt = build_chatbot_prompt(
                farmer_context=context_str,
                history=history,
                user_message=user_message,
            )

            # ── Stage 3: AI streaming ─────────────────────────────────────────
            yield sse("status", {"stage": "generating", "message": "Thinking..."})
            t3 = time.time()
            bot_response = ""
            is_fallback  = False
            parsed       = {}
            try:
                raw_tokens = []
                for token in ai_model_service.stream_complete(full_prompt):
                    raw_tokens.append(token)
                raw_llm      = "".join(raw_tokens)
                logger.info("[CHATBOT-STREAM] ③ LLM raw output:\n%s", raw_llm)
                parsed       = _parse_llm_response(raw_llm)
                bot_response = parsed["response"]
                yield sse("token", {"text": bot_response})
                logger.info("[CHATBOT-STREAM] ③ AI streamed (%dms) %d chars",
                            round((time.time() - t3) * 1000), len(bot_response))
            except Exception as exc:
                logger.warning("[CHATBOT-STREAM] ③ AI failed (%dms): %s",
                               round((time.time() - t3) * 1000), exc)
                if not bot_response:
                    bot_response = ChatbotService._build_fallback_response(user_message, context)
                    is_fallback  = True
                    yield sse("token", {"text": bot_response})

            total_ms = round((time.time() - t_start) * 1000)
            logger.info("[CHATBOT-STREAM] ✓ Total: %dms", total_ms)

            bot_msg = ChatRepository.create_message(
                conversation_id=conversation_id,
                sender="bot",
                message=bot_response,
                metadata={
                    "is_fallback": is_fallback,
                    "model":       "fallback" if is_fallback else ai_model_service.get_provider().name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_ms":    total_ms,
                    "urgency":     parsed.get("urgency", "medium"),
                    "actions":     parsed.get("actions", []),
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
            })

        except Exception as exc:
            total_ms = round((time.time() - t_start) * 1000)
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
