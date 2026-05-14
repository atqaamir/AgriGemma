import json
import logging
import time
from datetime import datetime

from app.services.ai_model_service import ai_model_service
from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import TaskIntelligencePromptBuilder

logger = logging.getLogger(__name__)


"move this to task generation!!"






# Module-level in-process cache.
# For multi-worker deployments, replace with a Redis-backed cache.
_CACHE: dict = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


class TaskIntelligenceService:
    """
    Generates an AI-driven task intelligence overview using Gemma4.
    Responses are cached per user for TTL seconds to avoid blocking
    the UI on every page load.  A rule-based fallback guarantees a
    useful response even when the AI model is unavailable.
    """

    @staticmethod
    def generate_intelligence(context: dict, user_id: int) -> dict:
        cache_key = f"task_intel_{user_id}"
        cached = _CACHE.get(cache_key)

        if cached and (time.monotonic() - cached["ts"]) < _CACHE_TTL_SECONDS:
            logger.debug("task_intelligence cache hit for user %s", user_id)
            return cached["data"]

        prompt = TaskIntelligencePromptBuilder.build(context)

        try:
            raw = ai_model_service.complete(prompt)
            intelligence = TaskIntelligenceService._parse_response(raw)
            intelligence["is_fallback"] = False
        except Exception as exc:
            logger.warning("AI intelligence failed (user=%s): %s", user_id, exc)
            intelligence = TaskIntelligenceService._build_rule_based_fallback(context)
            intelligence["is_fallback"] = True

        intelligence["generated_at"] = datetime.utcnow().isoformat() + "Z"

        _CACHE[cache_key] = {"ts": time.monotonic(), "data": intelligence}
        return intelligence

    @staticmethod
    def invalidate_cache(user_id: int) -> None:
        """Call this whenever tasks change and a fresh overview is needed."""
        _CACHE.pop(f"task_intel_{user_id}", None)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(raw) -> dict:
        """Extract and validate the JSON object from the Gemma response."""
        if isinstance(raw, dict):
            content = raw.get("response") or raw.get("text") or raw.get("output") or ""
        else:
            content = str(raw)

        # Locate the outermost JSON object in the response text
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end <= 0:
            raise ValueError("No JSON object found in Gemma response")

        parsed = json.loads(content[start:end])

        # Validate required keys are present
        required = {"summary", "priority_level", "recommendations", "urgent_actions", "risks", "insights"}
        if not required.issubset(parsed.keys()):
            raise ValueError(f"Gemma response missing keys: {required - parsed.keys()}")

        return parsed

    @staticmethod
    def _build_rule_based_fallback(context: dict) -> dict:
        """
        Deterministic fallback that mirrors the AI output schema.
        Guarantees the frontend always receives a valid intelligence object.
        """
        tasks = context.get("tasks", {})
        alerts = context.get("alerts", [])
        farm = context.get("farm", {})

        overdue = tasks.get("overdue_count", 0)
        critical = tasks.get("critical_count", 0)
        pending = tasks.get("pending_count", 0)
        high = tasks.get("high_priority_count", 0)

        # Determine overall priority
        if critical > 0 or overdue > 0:
            priority_level = "critical"
        elif high > 0:
            priority_level = "high"
        elif pending > 0:
            priority_level = "medium"
        else:
            priority_level = "low"

        # Build urgent actions
        urgent_actions: list[str] = []
        if overdue > 0:
            urgent_actions.append(f"Address {overdue} overdue task(s) immediately to prevent crop loss.")
        if critical > 0:
            urgent_actions.append(f"Complete {critical} critical-priority task(s) today.")
        for alert in alerts[:2]:
            if alert.get("level") == "high":
                urgent_actions.append(alert.get("message", ""))

        # Build recommendations from top pending tasks
        recommendations: list[str] = []
        for task in tasks.get("pending_list", [])[:4]:
            if not task.get("is_overdue"):
                loc = task.get("field_name") or task.get("crop_name") or "farm"
                recommendations.append(
                    f"Complete '{task['title']}' ({task.get('priority', 'medium')} priority) on {loc}."
                )
        if not recommendations:
            recommendations.append("Review all pending tasks and prioritize by due date.")

        # Build risks from high-level alerts
        risks = [
            {
                "risk": a.get("message", ""),
                "severity": a.get("level", "medium"),
                "mitigation": "Review field conditions and act promptly.",
            }
            for a in alerts
            if a.get("level") in ("high", "medium")
        ][:4]

        # Build insights from field data
        insights: list[dict] = []
        for field in farm.get("active_fields_data", [])[:3]:
            if field.get("moisture_level") is not None and field["moisture_level"] < 30:
                insights.append({
                    "insight": f"{field['name']} has low soil moisture ({field['moisture_level']}%). Irrigation may be needed.",
                    "category": "irrigation",
                })
            if (field.get("health_status") or "").lower() in ("poor", "alert", "critical"):
                insights.append({
                    "insight": f"{field['name']} health status is '{field['health_status']}'. Inspect for disease or stress.",
                    "category": "disease",
                })

        active_fields = farm.get("active_fields", 0)
        summary = (
            f"AI overview unavailable — showing rule-based analysis. "
            f"{active_fields} active field(s), {pending} pending task(s), "
            f"{overdue} overdue. Manual review recommended."
        )

        return {
            "summary": summary,
            "priority_level": priority_level,
            "recommendations": recommendations,
            "urgent_actions": urgent_actions,
            "risks": risks,
            "insights": insights,
        }
