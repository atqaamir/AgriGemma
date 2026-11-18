import logging

from app.utils import clock
from app.services.ai_model_service.ai_model_service import fast_complete as _fast_complete
from app.services.intelligence_service.chatbot_service.prompts._prompt_task_intelligence import (
    build_task_reasoning_prompt,
)

logger = logging.getLogger(__name__)


class TaskIntelligenceService:
    """
    AI explanation for a single (non-plan) task. Task insights and the farm report live in
    task_insights_service / farm_report_service.
    """

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

