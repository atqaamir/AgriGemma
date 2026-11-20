"""The farmer's answer to a "Decide: <crop> sowing" task (decision needed / overdue).

- sow_anyway: farmer_planned overrides (sowing tomorrow + cascaded harvest, irrigation start,
  fertilization) that the daily re-plan never moves; the plan task sync then creates
  "Sow <crop>" due tomorrow (a note says when this is against the AI recommendation).
  Completing that task records the actual sowing date as usual (farmer_completed wins).
- skip_season: seasonal_plan_entry.skipped_on = today → no plan events or tasks for the crop;
  the weekly plan shows "Skipped by the farmer".
- undo (weekly plan page): deletes the farmer_planned overrides / clears skipped_on and
  reopens the decision task; refused once sowing is recorded as done.

Each action completes (or reopens) the decision task with the reason in its history and then
re-plans like app startup (plan roll + forecast + plan task sync; no AI, no notifications).
"""
import logging
from datetime import timedelta

from app.extensions import db
from app.models.plan_event_override import PlanEventOverride
from app.models.seasonal_plan import SeasonalPlanEntry
from app.models.task import Task
from app.utils import clock

logger = logging.getLogger(__name__)

SOW_ANYWAY_REASON = "Farmer decision: sow anyway"


class DecisionError(ValueError):
    """Refused action (shown to the farmer)."""


def _fmt(d):
    return f"{d.day} {d.strftime('%b')}"


def _open_decision_task(user_id: int, task_id: int) -> tuple[Task, SeasonalPlanEntry]:
    from app.services.task_generation_service import DECISION_TASK_TYPE
    t = Task.query.get(task_id)
    if t is None or t.user_id != user_id or t.task_type != DECISION_TASK_TYPE:
        raise DecisionError("Decision task not found")
    if t.completed or not t.is_active:
        raise DecisionError("This decision is already closed")
    entry = SeasonalPlanEntry.query.get(t.seasonal_plan_entry_id) if t.seasonal_plan_entry_id else None
    if entry is None:
        raise DecisionError("The decision task has no seasonal plan entry")
    return t, entry


def _crop(entry) -> str:
    return entry.crop_name_rel.name if entry.crop_name_rel else f"Crop {entry.crop_name_id}"


def _record(task: Task, changes: list, updates: dict) -> None:
    from app.services.domain_service.task_service import TaskService
    TaskService.record_changes(task, changes, updates)


def _replan(user_id: int) -> dict:
    """Plan roll + forecast + plan task sync for today (no AI, no notifications)."""
    from app.agents.coordinator_agent import CoordinatorAgent
    return CoordinatorAgent().startup_forecast(user_id)


def recommended_option(task: Task) -> str | None:
    """The option key of the task's AI recommendation, or None."""
    from app.services.decision_recommendation_service import OPTIONS
    text = task.ai_explanation or ""
    return next((k for k, label in OPTIONS.items() if text.startswith(label + ".")), None)


def sow_anyway(user_id: int, task_id: int) -> dict:
    from app.repositories.plan_event_override_repository import PlanEventOverrideRepository
    from app.services.decision_recommendation_service import OPTIONS
    from app.services.plan_override_service import CASCADE_FROM_SOWING, PlanOverrideService
    task, entry = _open_decision_task(user_id, task_id)
    today = clock.today()
    day = today + timedelta(days=1)
    eff = PlanOverrideService.effective_dates(entry, today)
    if eff["sowing_done_on"]:
        raise DecisionError(f"Sowing is already recorded as done on {_fmt(eff['sowing_done_on'])}")
    previous = eff["sowing"]
    delta = (day - previous) if previous else None
    for row in PlanEventOverrideRepository.get_farmer_planned(entry.id):   # one decision at a time
        db.session.delete(row)
    base = {"seasonal_plan_entry_id": entry.id, "source": PlanEventOverride.SOURCE_FARMER_PLANNED,
            "as_of_date": today}
    db.session.add(PlanEventOverride(**base, event_type="sowing", original_date=previous, actual_date=day,
                                     reason=f"{SOW_ANYWAY_REASON} on {_fmt(day)} (decision task #{task.id})"))
    if delta:
        for etype in CASCADE_FROM_SOWING:
            if eff[etype]:
                db.session.add(PlanEventOverride(
                    **base, event_type=etype, original_date=eff[etype], actual_date=eff[etype] + delta,
                    reason=f"Cascaded from the farmer's decision to sow anyway on {_fmt(day)} "
                           f"({delta.days:+d} days, decision task #{task.id})"))
    db.session.commit()

    rec = recommended_option(task)
    against = rec is not None and rec != "sow_anyway"
    _record(task, [{"change_type": "completed", "original_value": False, "new_value": True,
                    "reason": f"Decided: sow anyway on {_fmt(day)}"}],
            {"completed": True, "completed_at": clock.now()})
    _replan(user_id)

    crop = _crop(entry)
    sow = (Task.query.filter(Task.user_id == user_id, Task.seasonal_plan_entry_id == entry.id,
                             Task.task_type == "planting", Task.completed.is_(False), Task.is_active.is_(True))
           .order_by(Task.id.desc()).first())
    if sow is not None:
        note = f"Sow anyway: the farmer decided to sow {crop} on {_fmt(day)} (no suitable day left in the window)."
        if against:
            note += f" This is against the AI recommendation ({OPTIONS[rec].lower()})."
        sow.notes = note if not sow.notes else f"{sow.notes}\n{note}"
        db.session.commit()
    logger.info("Decision task %s: sow anyway on %s (entry %s, against recommendation: %s, sow task %s)",
                task.id, day, entry.id, against, sow.id if sow else None)
    return {"decision": "sow_anyway", "date": day.isoformat(), "sow_task_id": sow.id if sow else None,
            "against_recommendation": against, "crop": crop}


def skip_season(user_id: int, task_id: int) -> dict:
    task, entry = _open_decision_task(user_id, task_id)
    today = clock.today()
    entry.skipped_on = today
    db.session.commit()
    _record(task, [{"change_type": "completed", "original_value": False, "new_value": True,
                    "reason": "Decided: skip this season"}],
            {"completed": True, "completed_at": clock.now()})
    _replan(user_id)
    logger.info("Decision task %s: %s skipped for the season (entry %s)", task.id, _crop(entry), entry.id)
    return {"decision": "skip_season", "crop": _crop(entry)}


def undo(user_id: int, entry_id: int) -> dict:
    """Undo "skip this season" or "sow anyway" for a seasonal entry."""
    from app.models.seasonal_plan import SeasonalPlan
    from app.repositories.plan_event_override_repository import PlanEventOverrideRepository
    from app.services.plan_override_service import PlanOverrideService
    from app.services.task_generation_service import DECISION_TASK_TYPE
    entry = SeasonalPlanEntry.query.get(entry_id)
    plan = SeasonalPlan.query.get(entry.plan_id) if entry else None
    if entry is None or plan is None or plan.user_id != user_id:
        raise DecisionError("Plan entry not found")
    today = clock.today()
    if PlanOverrideService.effective_dates(entry, today)["sowing_done_on"]:
        raise DecisionError("Sowing is already recorded as done – nothing to undo")
    planned = PlanEventOverrideRepository.get_farmer_planned(entry.id)
    if not entry.skipped_on and not planned:
        raise DecisionError("No decision to undo")
    undone = "skip this season" if entry.skipped_on else "sow anyway"
    entry.skipped_on = None
    for row in planned:
        db.session.delete(row)
    db.session.commit()
    task = (Task.query.filter(Task.user_id == user_id, Task.seasonal_plan_entry_id == entry.id,
                              Task.task_type == DECISION_TASK_TYPE, Task.completed.is_(True))
            .order_by(Task.id.desc()).first())
    if task is not None:
        _record(task, [{"change_type": "completed", "original_value": True, "new_value": False,
                        "reason": f"Decision undone ({undone})"}],
                {"completed": False, "completed_at": None, "is_active": True, "due_date": today,
                 "ai_explanation": None})
    _replan(user_id)
    logger.info("Entry %s: decision '%s' undone (decision task %s reopened)", entry.id, undone,
                task.id if task else None)
    return {"undone": undone, "decision_task_id": task.id if task else None, "crop": _crop(entry)}
