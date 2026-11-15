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
    def match_entry(user_id: int, crop_name_id: int, field_id: int = None, context: str = ""):
        """Find the active seasonal plan entry for a crop (and field, if known).

        With a field: crop + the field's soil type and water source must match.
        Without a field: crop alone, only if exactly one active entry fits.
        Zero or several matches → warning, None.
        """
        from app.models.seasonal_plan import SeasonalPlan
        from app.models.field import Field

        plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
        if not plan or crop_name_id is None:
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
        logger.warning(
            "No unique seasonal entry match (%s): user=%s crop=%s field=%s → %d candidates; nothing written",
            context, user_id, crop_name_id, field_id, len(candidates),
        )
        return None

    @staticmethod
    def done_events(entry, as_of: date) -> list:
        """Events the farmer has completed, for display ("done on <date>")."""
        farmer = PlanEventOverrideRepository.get_farmer_sowing(entry.id, as_of)
        if not farmer:
            return []
        return [{"event_type": "sowing", "date": farmer.actual_date.isoformat(), "status": "done"}]
