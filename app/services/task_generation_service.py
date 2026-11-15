import json
import logging
from collections import defaultdict
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
PLAN_EVENT_TASKS_BY_TYPE = {v[0]: k for k, v in PLAN_EVENT_TASKS.items()}   # task_type → event_type
# One task per seasonal entry and type for the whole lifecycle: when the plan moves the
# event, the task's due date moves with it (sync_plan_tasks).
ONE_TIME_TASK_TYPES = ("planting", "fertilization", "harvesting")
# Irrigation is recurring and date-bound: a task belongs to one date. When the plan changes
# its irrigation days, the task for a dropped date is DEACTIVATED and a task for a new date
# is CREATED (matched by entry, type and date) — irrigation tasks are never "moved".
EVENT_LABEL = {"planting": "Sowing", "fertilization": "Fertilization",
               "harvesting": "Harvest", "irrigation": "Irrigation"}


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
        """A plan task is never duplicated:
        - same entry, type and due date, in any state (a deactivated one is reactivated
          by sync_plan_tasks, not re-created);
        - one-time types (sowing, fertilization, harvest): any not-completed task of the
          entry and type, whatever its date (the sync moves it);
        - unlinked tasks (no seasonal entry): same title and due date.
        """
        q = Task.query.filter(Task.user_id == user_id)
        if entry is None:
            return q.filter(Task.title == title, Task.due_date == due).count() > 0
        q = q.filter(Task.seasonal_plan_entry_id == entry.id, Task.task_type == task_type)
        if q.filter(Task.due_date == due).count():
            return True
        return task_type in ONE_TIME_TASK_TYPES and q.filter(Task.completed.is_(False)).count() > 0

    # ------------------------------------------------------------------ #
    #  Keeping plan tasks in line with the weekly plan (Step C)
    # ------------------------------------------------------------------ #

    @staticmethod
    def sync_plan_tasks(user_id: int, as_of: date = None) -> dict:
        """After every re-plan (daily update, simulator): make the plan tasks match the
        active weekly plan (as_of..as_of+6). Fixed texts, no AI call.

        Only not-completed plan tasks with a seasonal_plan_entry_id are touched:
        - sowing / fertilization / harvest (one task per entry and type):
          event in the window -> the task's due date moves to it (a deactivated task is
          reactivated instead of creating a new one); event gone -> deactivated. A missed
          fertilization/harvest task (due date passed) stays as it is; sowing that is not
          done is always re-planned by the sowing window, so its task follows the plan.
        - irrigation (date-bound): deactivate + create, matched by entry, type and date,
          never moved. A task whose date is back in the plan is reactivated.
        Then missing tasks for today and tomorrow are created (generate_plan_tasks).
        Every change is recorded in the task's history (TaskService.record_changes).
        """
        as_of = as_of or clock.today()
        window_end = as_of + timedelta(days=6)
        summary = {"moved": [], "deactivated": [], "reactivated": [], "created": []}
        plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
        if not plan:
            logger.warning("Plan task sync: user=%s has no active weekly plan", user_id)
            return summary

        plan_dates = defaultdict(set)          # (entry id, task_type) -> dates in the window
        wentry_of, sowing_text = {}, {}
        for wentry in plan.entries:
            entry = PlanOverrideService.match_entry(user_id, wentry.crop_id, wentry.field_id, warn=False)
            if entry is None:
                continue
            wentry_of[entry.id] = wentry
            for a in json.loads(wentry.climate_adjustments or "[]"):
                if a.get("factor") == "sowing_window" and a.get("adjustment"):
                    sowing_text[entry.id] = a["adjustment"]
            for e in json.loads(wentry.week_events or "[]"):
                if e.get("event_type") in PLAN_EVENT_TASKS:
                    d = date.fromisoformat(e["date"])
                    if as_of <= d <= window_end:
                        plan_dates[(entry.id, PLAN_EVENT_TASKS[e["event_type"]][0])].add(d)

        tasks = (Task.query.filter(Task.user_id == user_id, Task.task_category == PLAN_TASK_CATEGORY,
                                   Task.completed.is_(False), Task.seasonal_plan_entry_id.isnot(None))
                 .order_by(Task.id).all())
        groups = defaultdict(list)
        for t in tasks:
            groups[(t.seasonal_plan_entry_id, t.task_type)].append(t)

        fmt = lambda d: f"{d.day} {d.strftime('%b')}"
        iso = lambda d: d.isoformat() if d else None

        def change(kind, old, new, reason):
            return {"change_type": kind, "original_value": old, "new_value": new, "reason": reason}

        for (entry_id, ttype), group in groups.items():
            label = EVENT_LABEL.get(ttype, ttype)
            dates = sorted(plan_dates.get((entry_id, ttype), ()))

            if ttype in ONE_TIME_TASK_TYPES:
                active = [t for t in group if t.is_active]
                if dates:
                    d = dates[0]
                    t = active[0] if active else group[-1]
                    reason = f"{label} {'moved' if active else 'back'} in the weekly plan ({fmt(d)})"
                    if ttype == "planting" and entry_id in sowing_text:
                        reason += f": {sowing_text[entry_id]}"
                    changes, updates = [], {}
                    if not t.is_active:
                        changes.append(change("is_active", False, True, reason))
                        updates["is_active"] = True
                    if t.due_date != d:
                        changes.append(change("due_date", iso(t.due_date), iso(d), reason))
                        updates["due_date"] = d
                    if changes:
                        wentry = wentry_of.get(entry_id)
                        if wentry is not None:
                            crop_name = t.title.split(" – ")[0].split(" ", 1)[-1]
                            updates["description"] = TaskGenerationService._plan_description(
                                wentry, PLAN_EVENT_TASKS_BY_TYPE[ttype], crop_name, t.field, d)
                        TaskService.record_changes(t, changes, updates)
                        summary["reactivated" if "is_active" in updates else "moved"].append(
                            f"#{t.id} {t.title} -> {d}")
                else:
                    reason = (sowing_text[entry_id] if ttype == "planting" and entry_id in sowing_text
                              else f"{label} no longer in the weekly plan ({fmt(as_of)}–{fmt(window_end)})")
                    for t in active:
                        if ttype != "planting" and t.due_date and t.due_date < as_of:
                            continue                       # missed fertilization/harvest: left as it is
                        TaskService.record_changes(t, [change("is_active", True, False, reason)],
                                                   {"is_active": False})
                        summary["deactivated"].append(f"#{t.id} {t.title} ({t.due_date})")
            else:
                # Irrigation: deactivate + create (by entry, type and date), never moved.
                for t in group:
                    if not t.due_date or not (as_of <= t.due_date <= window_end):
                        continue
                    in_plan = t.due_date in dates
                    if t.is_active and not in_plan:
                        TaskService.record_changes(t, [change(
                            "is_active", True, False,
                            f"{label} on {fmt(t.due_date)} no longer in the weekly plan")], {"is_active": False})
                        summary["deactivated"].append(f"#{t.id} {t.title} ({t.due_date})")
                    elif not t.is_active and in_plan:
                        TaskService.record_changes(t, [change(
                            "is_active", False, True,
                            f"{label} on {fmt(t.due_date)} back in the weekly plan")], {"is_active": True})
                        summary["reactivated"].append(f"#{t.id} {t.title} ({t.due_date})")

        for day in (as_of, as_of + timedelta(days=1)):
            summary["created"] += [f"#{t.id} {t.title} ({t.due_date})"
                                   for t in TaskGenerationService.generate_plan_tasks(user_id, day)["created"]]
        logger.info("Plan task sync for user=%s as_of=%s: %s", user_id, as_of, summary)
        return summary

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
            task.title for task in TaskService.get_tasks_by_user(user_id) or [] if task.is_pending
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
