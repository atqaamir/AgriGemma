"""Weekly planner service.

Orchestrates generate_weekly_plan → adjust_weekly_plan from RuleEngine,
persists the result to WeeklyPlan / WeeklyPlanEntry, and provides
formatted read helpers for the API layer.
"""

import json
from datetime import date, timedelta

from app.rules.rule_engine.rule_engine import RuleEngine
from app.repositories.weekly_plan_repository import WeeklyPlanRepository, WeeklyPlanEntryRepository
from app.services.rule_base_service import rule_base_service
from app.models.seasonal_plan import SeasonalPlan


class WeeklyPlannerService:

    # ------------------------------------------------------------------ #
    #  Internal formatter
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_plan(plan) -> dict:
        """Convert a WeeklyPlan ORM object into a clean, frontend-ready dict."""
        if plan is None:
            return {"status": "no_plan", "message": "No weekly plan found."}

        entries_output = []
        for entry in plan.entries:
            crop_obj   = rule_base_service.get_crop_by_id(entry.crop_id)
            stage_obj  = rule_base_service.get_stage_by_id(entry.growth_stage_id) if entry.growth_stage_id else None

            original_events = json.loads(entry.original_events)    if entry.original_events    else []
            events          = json.loads(entry.week_events)         if entry.week_events         else []
            adjustments     = json.loads(entry.climate_adjustments) if entry.climate_adjustments else []

            entries_output.append({
                "crop_id":                  entry.crop_id,
                "crop_name":                crop_obj.name if crop_obj else None,
                "field_id":                 entry.field_id,
                "growth_stage_id":          entry.growth_stage_id,
                "growth_stage":             stage_obj.name if stage_obj else None,
                "climate_adjustments_made": adjustments,
                "original_events":          original_events,
                "week_events":              events,
            })

        return {
            "plan_id":          plan.id,
            "week_start_date":  plan.week_start_date.isoformat(),
            "week_end_date":    plan.week_end_date.isoformat(),
            "generated_at":     plan.generated_at.isoformat() if plan.generated_at else None,
            "currently_active": plan.currently_active,
            "seasonal_plan_id": plan.seasonal_plan_id,
            "total_entries":    len(entries_output),
            "entries":          entries_output,
        }

    # ------------------------------------------------------------------ #
    #  Plan generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_plan(user_id: int, week_start_date: date = None) -> object:
        """Generate and persist a weekly plan for the given user and week.

        Parameters
        ----------
        user_id         : int
        week_start_date : date (defaults to today's Monday if omitted)

        Returns
        -------
        WeeklyPlan ORM object
        """
        if week_start_date is None:
            today = date.today()
            week_start_date = today - timedelta(days=today.weekday())   # Monday

        week_end_date = week_start_date + timedelta(days=6)

        # Deactivate any previously active plan for this user
        existing = WeeklyPlanRepository.get_active_by_user_id(user_id)
        if existing:
            WeeklyPlanRepository.update(existing, {"currently_active": False})

        # Resolve seasonal plan id (for reference / traceability)
        seasonal_plan = SeasonalPlan.query.filter_by(
            user_id=user_id, currently_active=True
        ).first()
        seasonal_plan_id = seasonal_plan.id if seasonal_plan else None

        # Step 1 — raw schedule
        raw_plan = RuleEngine.generate_weekly_plan(user_id, week_start_date)

        # Step 2 — apply climate adjustments (also filters events to current week)
        adjusted_plan = RuleEngine.adjust_weekly_plan(raw_plan, week_start_date)

        # Persist top-level plan
        plan = WeeklyPlanRepository.create({
            "user_id":          user_id,
            "week_start_date":  week_start_date,
            "week_end_date":    week_end_date,
            "currently_active": True,
            "seasonal_plan_id": seasonal_plan_id,
        })

        # Index raw events by crop_id for original_events lookup
        raw_by_crop = {r["crop_id"]: r["week_events"] for r in raw_plan}

        # Persist one entry per crop result
        for item in adjusted_plan:
            WeeklyPlanEntryRepository.create({
                "weekly_plan_id":      plan.id,
                "crop_id":             item["crop_id"],
                "field_id":            item.get("field_id"),
                "growth_stage_id":     item.get("growth_stage_id"),
                "original_events":     json.dumps(raw_by_crop.get(item["crop_id"], [])),
                "week_events":         json.dumps(item["week_events"]),
                "climate_adjustments": json.dumps(item.get("climate_adjustments_made", [])),
            })

        return plan

    # ------------------------------------------------------------------ #
    #  Read (raw ORM objects)
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_active_plan(user_id: int):
        return WeeklyPlanRepository.get_active_by_user_id(user_id)

    @staticmethod
    def get_all_plans(user_id: int):
        return WeeklyPlanRepository.get_by_user_id(user_id)

    # ------------------------------------------------------------------ #
    #  Read (formatted for frontend)
    # ------------------------------------------------------------------ #

    @staticmethod
    def show_active_plan(user_id: int) -> dict:
        """Return the user's active weekly plan formatted for the UI.

        Example response
        ----------------
        {
          "plan_id": 1,
          "week_start_date": "2026-05-15",
          "week_end_date": "2026-05-21",
          "generated_at": "2026-05-15T10:30:00",
          "currently_active": true,
          "seasonal_plan_id": 1,
          "total_entries": 2,
          "entries": [
            {
              "crop_id": 2,
              "crop_name": "Rice",
              "field_id": 1,
              "growth_stage_id": 2,
              "growth_stage": "Vegetative",
              "week_events": [
                {
                  "event_type": "sowing",
                  "date": "2026-05-16",
                  "climate_adjustments_made": [
                    {
                      "factor": "temperature",
                      "reasoning": "...",
                      "adjustment": "..."
                    }
                  ]
                }
              ]
            }
          ]
        }
        """
        plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
        if plan is None:
            return {
                "status":  "no_active_plan",
                "message": "No active weekly plan found for this user.",
            }
        return WeeklyPlannerService._format_plan(plan)

    @staticmethod
    def show_plan(plan_id: int) -> dict:
        """Return any weekly plan (active or not) formatted for the UI."""
        plan = WeeklyPlanRepository.get_by_id(plan_id)
        return WeeklyPlannerService._format_plan(plan)

    @staticmethod
    def show_all_plans(user_id: int) -> list:
        """Return all weekly plans for a user, each formatted for the UI."""
        plans = WeeklyPlanRepository.get_by_user_id(user_id)
        return [WeeklyPlannerService._format_plan(p) for p in plans]

    # ------------------------------------------------------------------ #
    #  Update / Delete
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_plan(plan_id: int, data: dict):
        """Only currently_active may be changed at the plan level."""
        plan = WeeklyPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        allowed = {k: v for k, v in data.items() if k == "currently_active"}
        return WeeklyPlanRepository.update(plan, allowed)

    @staticmethod
    def delete(plan_id: int):
        plan = WeeklyPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        WeeklyPlanRepository.delete(plan)   # cascades to entries
        return plan
