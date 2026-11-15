"""Actual-dates layer: effective event dates = seasonal plan + PlanEventOverride.

The seasonal plan is never modified here. See app/models/plan_event_override.py.
"""
import logging
from datetime import date, datetime

from app.models.plan_event_override import PlanEventOverride
from app.repositories.plan_event_override_repository import PlanEventOverrideRepository

logger = logging.getLogger(__name__)

# override event_type → SeasonalPlanEntry column ("MM/DD/YYYY" strings)
SEASONAL_COLUMNS = {
    "sowing":           "sowing",
    "fertilization":    "fertilization_date",
    "harvesting":       "harvesting",
    "irrigation_start": "irrigation_start_date",
}
CASCADE_FROM_SOWING = ("harvesting", "irrigation_start", "fertilization")


def _parse(s):
    if not s:
        return None
    return datetime.strptime(s, "%m/%d/%Y").date()


class PlanOverrideService:

    # ------------------------------------------------------------------ #
    #  Effective dates
    # ------------------------------------------------------------------ #

    @staticmethod
    def effective_dates(entry, as_of: date) -> dict:
        """Effective one-time event dates of a seasonal entry when planning for `as_of`.

        Returns {"sowing", "fertilization", "harvesting", "irrigation_start": date|None,
                 "sowing_done_on": date|None}. A farmer_completed sowing always wins:
        sowing is done and cannot be shifted by the forecast.
        """
        eff = {t: _parse(getattr(entry, col)) for t, col in SEASONAL_COLUMNS.items()}
        for o in PlanEventOverrideRepository.get_applicable(entry.id, as_of):
            eff[o.event_type] = o.actual_date
        farmer = PlanEventOverrideRepository.get_farmer_sowing(entry.id, as_of)
        eff["sowing_done_on"] = farmer.actual_date if farmer else None
        if farmer:
            eff["sowing"] = farmer.actual_date
        return eff

    # ------------------------------------------------------------------ #
    #  Matching a task / weekly entry to its seasonal plan entry
    # ------------------------------------------------------------------ #

    @staticmethod
    def match_entry(user_id: int, crop_name_id: int, field_id: int = None, context: str = "",
                    warn: bool = True):
        """Find the active seasonal plan entry for a crop (and field, if known).

        With a field: crop + the field's soil type and water source must match.
        Without a field: crop alone, only if exactly one active entry fits.
        Zero or several matches → warning, None.
        """
        from app.models.seasonal_plan import SeasonalPlan
        from app.models.field import Field

        plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
        if not plan or crop_name_id is None:
            if warn:
                logger.warning("No seasonal entry match (%s): user=%s crop=%s — no active plan or crop",
                               context, user_id, crop_name_id)
            return None
        candidates = [e for e in plan.entries if e.crop_name_id == crop_name_id]

        field = Field.query.get(field_id) if field_id else None
        if field is not None:
            candidates = [e for e in candidates
                          if e.soil_id == field.soil_type_id and e.water_source_id == field.water_source_id]

        if len(candidates) == 1:
            return candidates[0]
        if not warn:
            return None
        logger.warning(
            "No unique seasonal entry match (%s): user=%s crop=%s field=%s → %d candidates; nothing written",
            context, user_id, crop_name_id, field_id, len(candidates),
        )
        return None

    @staticmethod
    def active_crop_for_entry(entry, user_id: int):
        """The user's active crop (on an active field) that a seasonal entry describes:
        same crop, field with the entry's soil type and water source.

        Returns the Crop when exactly one fits, else None (the caller warns).
        """
        from app.models.crop import Crop
        from app.models.field import Field
        crops = (Crop.query.join(Field, Crop.field_id == Field.id)
                 .filter(Crop.user_id == user_id, Crop.crop_name_id == entry.crop_name_id,
                         Crop.currently_active.is_(True), Field.currently_active.is_(True),
                         Field.soil_type_id == entry.soil_id,
                         Field.water_source_id == entry.water_source_id)
                 .all())
        return crops[0] if len(crops) == 1 else None

    # ------------------------------------------------------------------ #
    #  Forecast shifts (daily update)
    # ------------------------------------------------------------------ #

    @staticmethod
    def sync_forecast_shifts(user_id: int, as_of: date, updated_entries: list) -> dict:
        """Make day `as_of`'s forecast_shift overrides match this run's decisions.

        updated_entries: output of RuleEngine.update_weekly_plan (with "event_shifts").
        A sowing shift cascades to harvesting, irrigation start and fertilization
        (rule D) unless that event has its own in-window shift. Identical existing
        rows are kept (no duplicates); changed ones are updated; rows no longer
        backed by a decision are deleted. Pass [] to clear the day.
        """
        from app.models.seasonal_plan import SeasonalPlan

        plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
        stats ={"created": 0, "unchanged": 0, "updated": 0, "deleted": 0}
        if not plan:
            return stats

        desired = {}   # (entry_id, event_type) -> {original_date, actual_date, reason}
        for item in updated_entries:
            shifts = item.get("event_shifts") or {}
            if not shifts:
                continue
            entry = PlanOverrideService.match_entry(
                user_id, item.get("crop_id"), item.get("field_id"), context="forecast shift")
            if entry is None:
                continue
            eff = PlanOverrideService.effective_dates(entry, as_of)

            sow = shifts.get("sowing")
            if sow and eff["sowing_done_on"]:
                logger.info("Entry %s: sowing done on %s by farmer — forecast sowing shift ignored",
                            entry.id, eff["sowing_done_on"])
                sow = None
            if sow:
                s_from, s_to = date.fromisoformat(sow["from"]), date.fromisoformat(sow["to"])
                delta = s_to - s_from
                desired[(entry.id, "sowing")] = {
                    "original_date": s_from, "actual_date": s_to, "reason": sow["reason"]}
                for etype in CASCADE_FROM_SOWING:
                    if etype in shifts or not eff[etype]:
                        continue
                    desired[(entry.id, etype)] = {
                        "original_date": eff[etype], "actual_date": eff[etype] + delta,
                        "reason": f"Cascaded from sowing — {sow['reason']}"}
            for etype in ("fertilization", "harvesting"):
                if etype in shifts:
                    sh = shifts[etype]
                    desired[(entry.id, etype)] = {
                        "original_date": date.fromisoformat(sh["from"]),
                        "actual_date": date.fromisoformat(sh["to"]), "reason": sh["reason"]}

        existing = PlanEventOverrideRepository.get_forecast_for_day([e.id for e in plan.entries], as_of)
        to_delete = []
        for row in existing:
            want = desired.pop((row.seasonal_plan_entry_id, row.event_type), None)
            if want is None:
                to_delete.append(row)
            elif all(getattr(row, k) == v for k, v in want.items()):
                stats["unchanged"] += 1
            else:
                PlanEventOverrideRepository.update(row, want)
                stats["updated"] += 1
        stats["deleted"] = PlanEventOverrideRepository.delete_many(to_delete)
        for (entry_id, etype), want in desired.items():
            PlanEventOverrideRepository.create({
                "seasonal_plan_entry_id": entry_id, "event_type": etype,
                "source": PlanEventOverride.SOURCE_FORECAST, "as_of_date": as_of, **want})
            stats["created"] += 1
        logger.info("Forecast overrides for user=%s as_of=%s: %s", user_id, as_of, stats)
        return stats

    # ------------------------------------------------------------------ #
    #  Farmer completion (task hook)
    # ------------------------------------------------------------------ #

    SOWING_TASK_TYPES = ("planting", "sowing")

    @staticmethod
    def _entry_for_task(task):
        """Seasonal entry of a task: its seasonal_plan_entry_id first (tasks generated
        from the weekly plan), else crop + field matching."""
        from app.models.crop import Crop
        from app.models.seasonal_plan import SeasonalPlanEntry
        if getattr(task, "seasonal_plan_entry_id", None):
            entry = SeasonalPlanEntry.query.get(task.seasonal_plan_entry_id)
            if entry is not None:
                return entry
            logger.warning("Task %s: seasonal_plan_entry_id %s not found — falling back to crop + field",
                           task.id, task.seasonal_plan_entry_id)
        crop = Crop.query.get(task.crop_id) if task.crop_id else None
        if crop is None:
            logger.warning("Task %s: no crop linked — no farmer override written", task.id)
            return None
        return PlanOverrideService.match_entry(
            task.user_id or crop.user_id, crop.crop_name_id, task.field_id or crop.field_id,
            context=f"task {task.id}")

    @staticmethod
    def record_farmer_sowing(task) -> list:
        """Sowing task marked done → farmer_completed overrides (sowing + cascades).

        actual_date = task.completed_at.date(). Harvest, irrigation start and
        fertilization move by (actual − previous sowing date, i.e. the effective date
        before completion, which may already be forecast-shifted). Nothing is written for
        a "Not Feasible" entry (the task itself stays done).
        """
        entry = PlanOverrideService._entry_for_task(task)
        if entry is None:
            return []
        crop = entry.crop_name_rel.name if entry.crop_name_rel else entry.crop_name_id
        if entry.feasibility == "Not Feasible":
            logger.warning("Task %s completed, but seasonal entry %s (%s) is Not Feasible — "
                           "no override written", task.id, entry.id, crop)
            return []

        actual = task.completed_at.date()
        existing = PlanEventOverrideRepository.get_farmer_sowing(entry.id, date.max)
        if existing and existing.task_id != task.id:
            logger.warning("Task %s: sowing of entry %s (%s) already recorded as done on %s by task %s — "
                           "no override written", task.id, entry.id, crop, existing.actual_date, existing.task_id)
            return []

        eff = PlanOverrideService.effective_dates(entry, actual)
        previous = eff["sowing"]            # last scheduled sowing date (may be forecast-shifted)
        delta = (actual - previous) if previous else None
        seasonal = datetime.strptime(entry.sowing, "%m/%d/%Y").date() if entry.sowing else None
        if previous == seasonal:
            compared = f"vs the planned sowing date {previous}"
        else:
            compared = f"vs the previous sowing date {previous}; seasonal plan {seasonal}"
        base = {"seasonal_plan_entry_id": entry.id, "source": PlanEventOverride.SOURCE_FARMER,
                "as_of_date": actual, "task_id": task.id}
        rows = [PlanEventOverrideRepository.create({
            **base, "event_type": "sowing", "original_date": previous, "actual_date": actual,
            "reason": f"Sowing done on {actual} (task #{task.id} '{task.title}')"})]
        if delta:
            for etype in CASCADE_FROM_SOWING:
                if eff[etype]:
                    rows.append(PlanEventOverrideRepository.create({
                        **base, "event_type": etype, "original_date": eff[etype],
                        "actual_date": eff[etype] + delta,
                        "reason": f"Cascaded from sowing done on {actual} "
                                  f"({delta.days:+d} day{'' if abs(delta.days) == 1 else 's'} {compared}, task #{task.id})"}))
        logger.info("Task %s: %d farmer_completed override(s) for entry %s (%s)",
                    task.id, len(rows), entry.id, crop)
        return rows

    @staticmethod
    def undo_farmer_task(task) -> int:
        """Sowing task un-completed → delete exactly that task's farmer_completed overrides."""
        rows = [r for r in PlanEventOverrideRepository.get_by_task(task.id)
                if r.source == PlanEventOverride.SOURCE_FARMER]
        n = PlanEventOverrideRepository.delete_many(rows)
        logger.info("Task %s un-completed: %d farmer_completed override(s) removed", task.id, n)
        return n

    DONE_LOOKBACK_DAYS = 7   # a completed event stays visible this many days before the window

    @staticmethod
    def done_events(entry, week_start: date, week_end: date) -> list:
        """Farmer-completed events to show in the weekly plan ("Sowed on <date>").

        Shown while the completion date is inside the window or up to
        DONE_LOOKBACK_DAYS before it.
        """
        from datetime import timedelta
        farmer = PlanEventOverrideRepository.get_farmer_sowing(entry.id, week_end)
        if not farmer:
            return []
        done_on = farmer.actual_date
        if not (week_start - timedelta(days=PlanOverrideService.DONE_LOOKBACK_DAYS) <= done_on <= week_end):
            return []
        return [{
            "event_type": "sowing",
            "date": done_on.isoformat(),
            "status": "done",
            "label": f"Sowed on {done_on.day} {done_on.strftime('%b %Y')}",
        }]
