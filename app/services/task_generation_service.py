import json
import logging
from datetime import date, timedelta

from app.models.seasonal_plan import SeasonalPlanEntry
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.repositories.weekly_plan_repository import WeeklyPlanRepository
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.task_service import TaskService
from app.services.intelligence_service.task_intelligence_service import TaskIntelligenceService
from app.services.intelligence_service.chatbot_service.context_aggregation_service import ContextAggregationService
from app.services.plan_override_service import PlanOverrideService
from app.services.rule_base_service import rule_base_service
from app.utils import clock

logger = logging.getLogger(__name__)

# weekly plan event_type → (task_type, title verb, priority)
PLAN_EVENT_TASKS = {
    "sowing":        ("planting",      "Sow",       "high"),
    "irrigation":    ("irrigation",    "Irrigate",  "medium"),
    "fertilization": ("fertilization", "Fertilize", "medium"),
    "harvesting":    ("harvesting",    "Harvest",   "high"),
}
PLAN_TASK_CATEGORY = "plan"


class TaskGenerationService:
    def __init__(self):
        pass

    def generate_daily_tasks(self, user_id: int, for_date: date = None) -> dict:
        """7 PM job: tomorrow's tasks.

        - Plan tasks: one task per weekly plan event dated `for_date` (default
          tomorrow), task_category "plan", no AI call.
        - Field-condition tasks (low moisture, poor health), with an AI explanation.
        """
        if for_date is None:
            for_date = clock.today() + timedelta(days=1)

        plan_result = self.generate_plan_tasks(user_id, for_date)
        field_tasks = self._generate_field_tasks(user_id)

        created = plan_result["created"] + field_tasks
        return {
            "created": len(created),
            "task_ids": [t.id for t in created],
            "plan_tasks": len(plan_result["created"]),
            "plan_skipped": plan_result["skipped"],
            "field_tasks": len(field_tasks),
            "for_date": for_date.isoformat(),
        }

    # ------------------------------------------------------------------ #
    #  Tasks from the weekly plan
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_plan_tasks(user_id: int, for_date: date) -> dict:
        """Create tasks for the active weekly plan's events on `for_date`.

        Linked to the seasonal plan entry (seasonal_plan_entry_id) and, when exactly
        one active crop on an active field matches it (crop + soil + water), to that
        crop and field; otherwise the task is created unlinked and a warning logged.
        Skipped: duplicates (same entry, task type and due date, or same title and due
        date), Not Feasible entries, and sowing that is already recorded as done.
        """
        plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
        created, skipped = [], []
        if not plan:
            logger.warning("Plan tasks: user=%s has no active weekly plan", user_id)
            return {"created": created, "skipped": skipped}

        for wentry in plan.entries:
            events = [e for e in json.loads(wentry.week_events or "[]")
                      if e.get("date") == for_date.isoformat() and e.get("event_type") in PLAN_EVENT_TASKS]
            if not events:
                continue

            crop_name_obj = rule_base_service.get_crop_by_id(wentry.crop_id)
            crop_name = crop_name_obj.name if crop_name_obj else f"Crop {wentry.crop_id}"
            entry = PlanOverrideService.match_entry(
                user_id, wentry.crop_id, wentry.field_id, context=f"plan tasks {crop_name}")
            if entry is not None and entry.feasibility == "Not Feasible":
                skipped += [f"{e['event_type']} {crop_name}: Not Feasible" for e in events]
                continue

            crop = PlanOverrideService.active_crop_for_entry(entry, user_id) if entry else None
            if entry is not None and crop is None:
                logger.warning("Plan tasks: no unique active crop + field for seasonal entry %s (%s) — "
                               "creating unlinked tasks", entry.id, crop_name)
            field = crop.field if crop else None

            for event in events:
                etype = event["event_type"]
                task_type, verb, priority = PLAN_EVENT_TASKS[etype]

                if etype == "sowing" and entry is not None:
                    done_on = PlanOverrideService.effective_dates(entry, for_date)["sowing_done_on"]
                    if done_on:
                        skipped.append(f"sowing {crop_name}: already done on {done_on}")
                        continue

                title = f"{verb} {crop_name}" + (f" – {field.name}" if field else "")
                if TaskGenerationService._plan_task_exists(user_id, entry, task_type, title, for_date):
                    skipped.append(f"{etype} {crop_name}: task already exists")
                    continue

                task = TaskService.create_task({
                    "title":                  title,
                    "priority":               priority,
                    "task_type":              task_type,
                    "task_category":          PLAN_TASK_CATEGORY,
                    "due_date":               for_date,
                    "description":            TaskGenerationService._plan_description(
                                                  wentry, etype, crop_name, field, for_date),
                    "crop_id":                crop.id if crop else None,
                    "field_id":               field.id if field else None,
                    "user_id":                user_id,
                    "seasonal_plan_entry_id": entry.id if entry else None,
                })
                created.append(task)

        logger.info("Plan tasks for user=%s on %s: %d created, %d skipped %s",
                    user_id, for_date, len(created), len(skipped), skipped)
        return {"created": created, "skipped": skipped}

    @staticmethod
    def _plan_task_exists(user_id, entry, task_type, title, due) -> bool:
        q = Task.query.filter(Task.user_id == user_id, Task.due_date == due, Task.is_active.is_(True))
        if entry is not None:
            return q.filter(Task.seasonal_plan_entry_id == entry.id, Task.task_type == task_type).count() > 0
        return q.filter(Task.title == title).count() > 0

    @staticmethod
    def _plan_description(wentry, etype, crop_name, field, day) -> str:
        where = f" on {field.name}" if field else ""
        text = f"From the weekly plan: {etype} of {crop_name}{where} on {day.day} {day.strftime('%b %Y')}."
        if etype == "sowing":
            adjustments = json.loads(wentry.climate_adjustments or "[]")
            window = next((a for a in adjustments if a.get("factor") == "sowing_window"), None)
            if window and window.get("adjustment"):
                text += f" {window['adjustment']}."
        return text

    # ------------------------------------------------------------------ #
    #  Field-condition tasks (unchanged behaviour)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _generate_field_tasks(user_id: int) -> list:
        fields = FieldService.get_fields_by_user(user_id) or []
        existing_titles = {
            task.title for task in TaskService.get_tasks_by_user(user_id) or [] if not task.completed
        }
        context = None
        created_tasks = []

        def create(data):
            nonlocal context
            if context is None:
                context = ContextAggregationService.build_task_context(user_id)
            task = TaskService.create_task(data)
            task.ai_explanation = TaskIntelligenceService.generate_task_explanation(task, context)
            TaskRepository.update(task, {"ai_explanation": task.ai_explanation})
            created_tasks.append(task)
            existing_titles.add(data["title"])

        for field in [f for f in fields if getattr(f, "currently_active", False)]:
            if field.moisture_level is not None and field.moisture_level < 30:
                title = f"Irrigate {field.name}"
                if title not in existing_titles:
                    create({
                        "title": title,
                        "priority": "high",
                        "task_type": "irrigation",
                        "task_category": "field",
                        "description": f"Soil moisture is low at {field.moisture_level}% for {field.name}.",
                        "field_id": field.id,
                        "user_id": user_id,
                    })

            if (getattr(field, "health_status", "") or "").lower() in ("poor", "alert", "critical"):
                title = f"Inspect {field.name} for stress or disease"
                if title not in existing_titles:
                    create({
                        "title": title,
                        "priority": "high",
                        "task_type": "inspection",
                        "task_category": "field",
                        "description": f"Field health status is {field.health_status}. Schedule inspection for {field.name}.",
                        "field_id": field.id,
                        "user_id": user_id,
                    })

            # NOTE: a "Review <crop> at <stage> stage" task used field.crop, which does not
            # exist (the relationship is field.crops, a list), so it never ran. Not fixed
            # here: it needs the active crop picked from the list (not a one-line change).

        return created_tasks
