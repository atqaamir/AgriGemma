"""
AI Prompt Test Endpoint
GET /test/ai  — runs all 4 prompt types against real DB data and returns responses.

Usage:
    curl http://localhost:5000/test/ai
    curl http://localhost:5000/test/ai?prompt=1    (chatbot only)
    curl http://localhost:5000/test/ai?prompt=2    (task intelligence only)
    curl http://localhost:5000/test/ai?prompt=3    (alert explanation only)
    curl http://localhost:5000/test/ai?prompt=4    (weather change advisory only)
"""

import time
import logging

from flask import Blueprint, jsonify, request

from app.services.ai_model_service import ai_model_service

logger = logging.getLogger(__name__)

test_ai_bp = Blueprint("test_ai", __name__)

USER_ID = 1  # Uses the seeded demo user


@test_ai_bp.route("/", methods=["GET"])
def test_all_prompts():
    """
    Fire all 4 AI prompts using real farm data and return each response with timing.
    Pass ?prompt=N to run a single prompt.
    """
    only = request.args.get("prompt", type=int)

    results = {
        "provider": _safe(lambda: ai_model_service.get_provider().name),
    }

    if only is None or only == 1:
        results["1_chatbot"] = _test_chatbot()

    if only is None or only == 2:
        results["2_task_intelligence"] = _test_task_intelligence()

    if only is None or only == 3:
        results["3_alert_explanation"] = _test_alert_explanation()

    if only is None or only == 4:
        results["4_weather_change_advisory"] = _test_weather_change_advisory()

    return jsonify(results), 200


# ── Individual prompt tests ────────────────────────────────────────────────────

def _test_chatbot():
    """
    Prompt 1: Chatbot answers a farmer question.
    Uses a full conversation so history and context are included.
    """
    try:
        from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService

        conv_id = ChatbotService.get_or_create_conversation(USER_ID)
        t0 = time.monotonic()
        result = ChatbotService.send_message(
            USER_ID,
            conv_id,
            "Why are you asking me to do irrigation tasks in May? My father and grandfather never did this.",
        )
        return {
            "ok": True,
            "question": "Why are you asking me to do irrigation tasks in May?",
            "response": result["bot_message"],
            "provider": result["metadata"].get("model"),
            "is_fallback": result["metadata"].get("is_fallback"),
            "ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        logger.exception("test_chatbot failed")
        return {"ok": False, "error": str(exc)}


def _test_task_intelligence():
    """
    Prompt 2: Dashboard AI overview — summarises tasks/risks/insights using rules.
    """
    try:
        from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
        from app.services.task_intelligence_service import TaskIntelligenceService

        TaskIntelligenceService.invalidate_cache(USER_ID)
        context = ContextAggregationService.build_task_context(USER_ID)
        t0 = time.monotonic()
        result = TaskIntelligenceService.generate_intelligence(context, USER_ID)
        return {
            "ok": True,
            "summary": result.get("summary"),
            "priority_level": result.get("priority_level"),
            "recommendations": result.get("recommendations", []),
            "is_fallback": result.get("is_fallback"),
            "rules_in_context": bool(context.get("rules")),
            "ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        logger.exception("test_task_intelligence failed")
        return {"ok": False, "error": str(exc)}


def _test_alert_explanation():
    """
    Prompt 3: Alert explanation — detects live alerts and generates AI explanation.
    """
    try:
        from app.services.domain_service.notification_service import NotificationService

        t0 = time.monotonic()
        result = NotificationService().generate_alerts_with_explanation(USER_ID)
        return {
            "ok": True,
            "alert_count": result["alert_count"],
            "alerts": [
                {"level": a.get("level"), "message": a.get("message")}
                for a in result["alerts"]
            ],
            "explanation": result["explanation"],
            "ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        logger.exception("test_alert_explanation failed")
        return {"ok": False, "error": str(exc)}


def _test_weather_change_advisory():
    """
    Prompt 4: Weather-change advisory — explains why tasks changed after a weather update.
    """
    try:
        from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
        from app.services.intelligence_service.advisory_service import AdvisoryService

        context = ContextAggregationService.build_task_context(USER_ID)
        t0 = time.monotonic()
        advisory = AdvisoryService.generate_weather_change_advisory(USER_ID, context)
        return {
            "ok": True,
            "farmer_name": context.get("farmer_name"),
            "pending_task_count": context.get("tasks", {}).get("pending_count", 0),
            "rules_in_context": bool(context.get("rules")),
            "advisory": advisory,
            "ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        logger.exception("test_weather_change_advisory failed")
        return {"ok": False, "error": str(exc)}


# ── Utility ────────────────────────────────────────────────────────────────────

def _safe(fn):
    try:
        return fn()
    except Exception as exc:
        return f"error: {exc}"
