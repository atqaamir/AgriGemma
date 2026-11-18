"""
AI Prompt Test Endpoint
GET /test/ai  — runs the 3 prompt types against real DB data and returns responses.

Usage:
    curl http://localhost:5000/test/ai
    curl http://localhost:5000/test/ai?prompt=1    (chatbot only)
    curl http://localhost:5000/test/ai?prompt=2    (task insights only — stores a report)
    curl http://localhost:5000/test/ai?prompt=3    (alert explanation only)
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
    Fire all 3 AI prompts using real farm data and return each response with timing.
    Pass ?prompt=N to run a single prompt.
    """
    only = request.args.get("prompt", type=int)

    results = {
        "provider": _safe(lambda: ai_model_service.get_provider().name),
    }

    if only is None or only == 1:
        results["1_chatbot"] = _test_chatbot()

    if only is None or only == 2:
        results["2_task_insights"] = _test_task_insights()

    if only is None or only == 3:
        results["3_alert_explanation"] = _test_alert_explanation()

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


def _test_task_insights():
    """
    Prompt 2: Task insights — signals → one AI call → validated priority order and insights.
    """
    try:
        from app.services import task_insights_service

        t0 = time.monotonic()
        result = task_insights_service.generate(USER_ID)
        data = result["data"]
        return {
            "ok": True,
            "basic_summary": data.get("basic_summary"),
            "error": data.get("error"),
            "priority_order": [f"{x['title']} – {x['reason']}" for x in data.get("priority_order", [])],
            "insights": [f"{x['title']}: {x['explanation']} ({', '.join(x['evidence'])})"
                         for x in data.get("insights", [])],
            "dropped": len(data.get("dropped", [])),
            "ms": round((time.monotonic() - t0) * 1000),
        }
    except Exception as exc:
        logger.exception("test_task_insights failed")
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


# ── Utility ────────────────────────────────────────────────────────────────────

def _safe(fn):
    try:
        return fn()
    except Exception as exc:
        return f"error: {exc}"
