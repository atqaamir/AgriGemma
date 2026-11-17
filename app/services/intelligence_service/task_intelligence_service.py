import json
import logging
from datetime import datetime, timezone

from app.utils import clock
from app.services.ai_model_service.ai_model_service import fast_complete as _fast_complete
from app.services.ai_model_service.ai_model_service import fast_complete_json as _fast_complete_json
from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import (
    TaskIntelligencePromptBuilder,
    build_task_reasoning_prompt,
)

logger = logging.getLogger(__name__)








class TaskIntelligenceService:
    """
    Generates AI task intelligence and task-specific explanations using Gemma.
    Cache is intentionally removed so all intelligence is based on current farm state.
    """

    @staticmethod
    def generate_intelligence(context: dict, user_id: int) -> dict:
        tasks = context.get("tasks", {})
        farm  = context.get("farm", {})
        logger.info(
            "[intelligence] user=%s | fields=%s active=%s | crops=%s | "
            "tasks: pending=%s overdue=%s critical=%s high=%s",
            user_id,
            farm.get("total_fields", 0), farm.get("active_fields", 0),
            farm.get("total_crops", 0),
            tasks.get("pending_count", 0), tasks.get("overdue_count", 0),
            tasks.get("critical_count", 0), tasks.get("high_priority_count", 0),
        )

        prompt = TaskIntelligencePromptBuilder.build(context)
        logger.info("[intelligence] prompt built — %d chars", len(prompt))
        logger.debug("[intelligence] full prompt:\n%s", prompt)

        try:
            raw = _fast_complete_json(prompt)
            logger.debug("[intelligence] raw response (%d chars): %s", len(raw), raw[:500] if raw else "<empty>")

            if not raw:
                raise ValueError("AI provider returned empty response")

            intelligence = TaskIntelligenceService._parse_response(raw)
            ai_level = intelligence.get("priority_level")
            # Override priority_level deterministically — Gemma is unreliable for this field
            intelligence["priority_level"] = TaskIntelligenceService._compute_priority_level(tasks)
            intelligence["is_fallback"] = False
            logger.info("[intelligence] success — priority_level=%s (ai returned: %s)",
                        intelligence["priority_level"], ai_level)
        except Exception as exc:
            logger.warning("[intelligence] failed (user=%s): %s", user_id, exc)
            intelligence = TaskIntelligenceService._build_rule_based_fallback(context)
            intelligence["is_fallback"] = True

        intelligence["generated_at"] = datetime.now(timezone.utc).isoformat()
        return intelligence

    @staticmethod
    def generate_task_explanation(task, context: dict) -> str:
        try:
            prompt = build_task_reasoning_prompt(
                {
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority,
                    "due_date": str(task.due_date) if task.due_date else None,
                    "field_name": task.field.name if task.field else None,
                    "crop_name": task.crop.name if task.crop else None,
                    "is_overdue": bool(task.due_date and task.due_date < clock.today()),
                },
                {
                    "farmer_name": context.get("farmer_name", "Farmer"),
                    "weather": context.get("weather", {}),
                    "rules": context.get("rules", ""),
                },
            )
            return TaskIntelligenceService._clean_text(_fast_complete(prompt))
        except Exception as exc:
            logger.warning("AI task explanation failed for task %s: %s", getattr(task, "id", None), exc)
            return (
                task.description
                or f"This task is important because of current farm conditions affecting {task.field.name if task.field else 'your farm'}."
            )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _clean_text(raw) -> str:
        if isinstance(raw, dict):
            raw = raw.get("response") or raw.get("text") or raw.get("output") or ""
        return str(raw).strip()

    @staticmethod
    def _parse_response(raw) -> dict:
        """Extract and validate the JSON object from the Gemma response."""
        if isinstance(raw, dict):
            content = raw.get("response") or raw.get("text") or raw.get("output") or ""
        else:
            content = str(raw)

        logger.debug("[parse] input length=%d | preview: %r", len(content), content[:300])

        start = content.find("{")
        end   = content.rfind("}") + 1
        if start == -1 or end <= 0:
            logger.error(
                "[parse] no JSON object found — content was %d chars. "
                "Preview: %r",
                len(content), content[:400] if content else "<empty>",
            )
            raise ValueError("No JSON object found in Gemma response")

        if content.strip() in ("{}", "{ }"):
            raise ValueError("AI provider returned empty JSON — likely a timeout")

        json_str = content[start:end]
        logger.debug("[parse] extracted JSON slice [%d:%d] (%d chars)", start, end, len(json_str))

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error(
                "[parse] JSON decode error: %s | extracted slice: %r",
                exc, json_str[:400],
            )
            raise ValueError(f"Malformed JSON in Gemma response: {exc}") from exc

        required = {"summary", "priority_level", "recommendations", "urgent_actions", "risks", "insights"}
        missing  = required - parsed.keys()
        if missing:
            logger.error("[parse] missing keys: %s | got keys: %s", missing, list(parsed.keys()))
            raise ValueError(f"Gemma response missing keys: {missing}")

        return parsed

    @staticmethod
    def _compute_priority_level(tasks: dict) -> str:
        if tasks.get("critical_count", 0) > 0:
            return "critical"
        if tasks.get("high_priority_count", 0) > 0 or tasks.get("overdue_count", 0) > 0:
            return "high"
        if tasks.get("pending_count", 0) > 0:
            return "medium"
        return "low"

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
        if critical > 0:
            priority_level = "critical"
        elif high > 0 or overdue > 0:
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
