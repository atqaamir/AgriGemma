import json
import logging
from datetime import datetime, timezone

from app.services.ai_model_service import ai_model_service
from app.services.ai_model_service.ai_model_service import fast_complete as _fast_complete
from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import (
    TaskIntelligencePromptBuilder,
    build_task_reasoning_prompt,
    build_task_update_reasoning_prompt,
    build_critical_tasks_overview_prompt,
    build_dashboard_oneliner_prompt,
)

logger = logging.getLogger(__name__)








class TaskIntelligenceService:
    """
    Generates AI task intelligence and task-specific explanations using Gemma.
    Cache is intentionally removed so all intelligence is based on current farm state.
    """

    @staticmethod
    def generate_intelligence(context: dict, user_id: int) -> dict:
        prompt = TaskIntelligencePromptBuilder.build(context)

        try:
            raw = _fast_complete(prompt)
            intelligence = TaskIntelligenceService._parse_response(raw)
            intelligence["is_fallback"] = False
        except Exception as exc:
            logger.warning("AI intelligence failed (user=%s): %s", user_id, exc)
            intelligence = TaskIntelligenceService._build_rule_based_fallback(context)
            intelligence["is_fallback"] = True

        intelligence["generated_at"] = datetime.now(timezone.utc).isoformat()
        return intelligence

    @staticmethod
    def generate_dashboard_oneliner(context: dict, user_id: int) -> dict:
        """
        Lightweight one-sentence dashboard header summary.
        Runs on Ollama (local Gemma 4) — fast, minimal context, no JSON parsing.
        Separate from generate_intelligence() so the dashboard card doesn't need
        to fire the full JSON intelligence prompt just to get one sentence.
        """
        try:
            prompt = build_dashboard_oneliner_prompt(context)
            raw    = _fast_complete(prompt)
            text   = TaskIntelligenceService._clean_text(raw)
            return {
                "summary":      text,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback":  False,
            }
        except Exception as exc:
            logger.warning("Dashboard one-liner failed (user=%s): %s", user_id, exc)
            return {
                "summary":      TaskIntelligenceService._build_dashboard_oneliner_fallback(context),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback":  True,
            }

    @staticmethod
    def generate_task_overview(context: dict, user_id: int) -> dict:
        try:
            prompt = build_critical_tasks_overview_prompt(
                context.get("tasks", {}).get("pending_list", []),
                {
                    "farmer_name": context.get("farmer_name"),
                    "weather": context.get("weather", {}),
                    "rules": context.get("rules", ""),
                },
            )
            raw = _fast_complete(prompt)
            return {
                "summary": TaskIntelligenceService._clean_text(raw),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback": False,
            }
        except Exception as exc:
            logger.warning("AI task overview failed (user=%s): %s", user_id, exc)
            return {
                "summary": TaskIntelligenceService._build_task_overview_fallback(context),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "is_fallback": True,
            }

    @staticmethod
    def generate_task_update_explanation(task, old_priority: str, context: dict, change_reason: str = "") -> str:
        """
        Explain to the farmer why a task's priority changed.

        task         — ORM Task object
        old_priority — priority string before the update (e.g. "medium")
        context      — {farmer_name, weather, rules}
        change_reason — optional free-text reason for the change
        """
        try:
            prompt = build_task_update_reasoning_prompt(
                {
                    "title":         task.title,
                    "description":   task.description,
                    "priority":      task.priority,
                    "old_priority":  old_priority,
                    "due_date":      str(task.due_date) if task.due_date else None,
                    "field_name":    task.field.name if task.field else None,
                    "crop_name":     task.crop.name if task.crop else None,
                    "is_overdue":    bool(task.due_date and task.due_date < __import__("datetime").date.today()),
                    "change_reason": change_reason,
                },
                context,
            )
            return TaskIntelligenceService._clean_text(_fast_complete(prompt))
        except Exception as exc:
            logger.warning("AI task update explanation failed for task %s: %s", getattr(task, "id", None), exc)
            old = old_priority.capitalize() if old_priority else "Previous"
            new = (task.priority or "updated").capitalize()
            return (
                f"This task was escalated from {old} to {new} priority"
                + (f" on {task.field.name}" if task.field else "")
                + ". Please review current field conditions and act accordingly."
            )

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
                    "is_overdue": bool(task.due_date and task.due_date < datetime.now(timezone.utc).date()),
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

    @staticmethod
    def _build_dashboard_oneliner_fallback(context: dict) -> str:
        tasks  = context.get("tasks") or {}
        farm   = context.get("farm") or {}
        fields = farm.get("active_fields") or 0
        overdue  = tasks.get("overdue_count") or 0
        critical = tasks.get("critical_count") or 0
        pending  = tasks.get("pending_count") or 0
        if overdue:
            return f"{fields} active fields with {overdue} overdue task(s) requiring immediate attention."
        if critical:
            return f"{fields} active fields with {critical} critical task(s) — act today."
        if pending:
            return f"{fields} active fields, {pending} task(s) pending — farm is on track."
        return f"{fields} active fields — no urgent tasks right now."

    @staticmethod
    def invalidate_cache(user_id: int) -> None:
        """No-op cache invalidation retained for compatibility."""
        return None

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
    def _build_task_overview_fallback(context: dict) -> str:
        tasks = [t for t in context.get("tasks", {}).get("pending_list", []) if t.get("priority") in ("critical", "high")]
        if not tasks:
            return "There are no critical or high-priority tasks right now."

        top = tasks[0]
        field = top.get("field_name") or top.get("crop_name") or "your farm"
        count = len(tasks)
        overdue = sum(1 for t in tasks if t.get("is_overdue"))
        overdue_phrase = f" {overdue} are overdue." if overdue else ""
        return (
            f"{count} urgent tasks need attention today, starting with '{top['title']}' for {field}.{overdue_phrase}"
        )

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
