"""Weekly planner service.

Orchestrates generate_weekly_plan → adjust_weekly_plan from RuleEngine,
persists the result to WeeklyPlan / WeeklyPlanEntry, and provides
formatted read helpers for the API layer.
"""

import json
from datetime import date, datetime, timedelta

from app.rules.rule_engine.rule_engine import RuleEngine
from app.repositories.weekly_plan_repository import WeeklyPlanRepository, WeeklyPlanEntryRepository
from app.services.rule_base_service import rule_base_service
from app.models.seasonal_plan import SeasonalPlan
from app.utils import clock
from app.extensions import db


class WeeklyPlannerService:

    # ------------------------------------------------------------------ #
    #  Internal formatter
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_plan(plan) -> dict:
        """Convert a WeeklyPlan ORM object into a clean, frontend-ready dict."""
        if plan is None:
            return {"status": "no_plan", "message": "No weekly plan found."}

        from app.services.plan_override_service import PlanOverrideService

        entries_output = []
        for entry in plan.entries:
            crop_obj   = rule_base_service.get_crop_by_id(entry.crop_id)
            stage_obj  = rule_base_service.get_stage_by_id(entry.growth_stage_id) if entry.growth_stage_id else None

            original_events = json.loads(entry.original_events)    if entry.original_events    else []
            events          = json.loads(entry.week_events)         if entry.week_events         else []
            adjustments     = json.loads(entry.climate_adjustments) if entry.climate_adjustments else []

            # Events the farmer already completed (e.g. sowing), shown as "done on <date>"
            seasonal_entry = PlanOverrideService.match_entry(
                plan.user_id, entry.crop_id, entry.field_id, warn=False)
            done = (PlanOverrideService.done_events(seasonal_entry, plan.week_start_date, plan.week_end_date)
                    if seasonal_entry else [])
            # planned | window_set | no_suitable_day | decision_needed | overdue | farmer_planned |
            # done | skipped | None (no sowing window)
            skipped_on = seasonal_entry.skipped_on if seasonal_entry is not None else None
            sowing_status = "done" if done else "skipped" if skipped_on else next(
                (a.get("status") for a in adjustments if a.get("factor") == "sowing_window"), None)
            farmer_planned = (PlanOverrideService.effective_dates(seasonal_entry, plan.week_start_date)
                              ["sowing_farmer_planned"] if seasonal_entry is not None and not done else None)

            entries_output.append({
                "sowing_status":            sowing_status,
                "crop_id":                  entry.crop_id,
                "crop_name":                crop_obj.name if crop_obj else None,
                "field_id":                 entry.field_id,
                "growth_stage_id":          entry.growth_stage_id,
                "growth_stage":             stage_obj.name if stage_obj else None,
                "climate_adjustments_made": adjustments,
                "original_events":          original_events,
                "week_events":              events,
                "done_events":              done,
                "seasonal_entry_id":        seasonal_entry.id if seasonal_entry is not None else None,
                "skipped_on":               skipped_on.isoformat() if skipped_on else None,
                "farmer_planned":           farmer_planned.isoformat() if farmer_planned else None,
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
    def _get_seasonal_plan_id(user_id: int) -> int | None:
        """Return the active seasonal plan id for this user, or None."""
        seasonal_plan = SeasonalPlan.query.filter_by(
            user_id=user_id, currently_active=True
        ).first()
        return seasonal_plan.id if seasonal_plan else None

    @staticmethod
    def _persist_entries(plan, adjusted_plan: list, raw_by_crop: dict) -> None:
        """Create WeeklyPlanEntry rows for each item in adjusted_plan."""
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

    @staticmethod
    def generate_plan(user_id: int, week_start_date: date = None) -> object:
        """Generate and persist a weekly plan for the given user and week.

        Parameters
        ----------
        user_id         : int
        week_start_date : date (defaults to today if omitted — the weekly plan
                          is a rolling 7-day window today..today+6)

        Returns
        -------
        WeeklyPlan ORM object
        """
        if week_start_date is None:
            week_start_date = clock.today()

        week_end_date = week_start_date + timedelta(days=6)

        # Deactivate any previously active plan for this user
        existing = WeeklyPlanRepository.get_active_by_user_id(user_id)
        if existing:
            WeeklyPlanRepository.update(existing, {"currently_active": False})

        # Resolve seasonal plan id (for reference / traceability)
        seasonal_plan_id = WeeklyPlannerService._get_seasonal_plan_id(user_id)

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
        WeeklyPlannerService._persist_entries(plan, adjusted_plan, raw_by_crop)

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
    def update_plan(user_id: int, as_of_date=None, notify: bool = True) -> str:
        """Update the active weekly plan using forecast weather from as_of_date onwards.

        Loads original events from DB, re-applies adjustments using forecast weather
        (incl. the sowing window), persists week_events and climate_adjustments, and
        records one-time event shifts as overrides. No AI calls. The only notification
        is the sowing decision (once per crop, on the day it happens — also on days
        without a plan impact); notify=False (app startup) sends none.
        """
        from app.models.field import Field
        from app.services.domain_service.user_service import UserService
        from app.utils.enums_ import Status

        if as_of_date is None:
            as_of_date = clock.today()

        plan = WeeklyPlanRepository.get_active_by_user_id(user_id)
        if not plan:
            return Status.FAILED

        # Entries built from the seasonal plan have no field_id; fall back to the
        # user's location (as RuleEngine.generate_weekly_plan does) so forecast
        # lookups still work.
        user_location = UserService.get_user_location(user_id)

        from app.services.plan_override_service import PlanOverrideService

        raw_entries = []
        for entry in plan.entries:
            field = Field.query.get(entry.field_id) if entry.field_id else None
            original_events = json.loads(entry.original_events) if entry.original_events else []
            # Sowing window: planned (seasonal) sowing date + effective dates as of today
            seasonal_entry = PlanOverrideService.match_entry(user_id, entry.crop_id, entry.field_id, warn=False)
            if seasonal_entry is not None and seasonal_entry.skipped_on:
                continue            # skipped by the farmer: no forecast re-plan, no events
            planned_sowing = (datetime.strptime(seasonal_entry.sowing, "%m/%d/%Y").date()
                              if seasonal_entry and seasonal_entry.sowing else None)
            eff = PlanOverrideService.effective_dates(seasonal_entry, as_of_date) if seasonal_entry else None
            sowing_window = (RuleEngine._sowing_window_info(planned_sowing, eff)
                             if planned_sowing else None)
            irrigation_period = RuleEngine._irrigation_period_info(eff) if eff else None
            raw_entries.append({
                "crop_id":         entry.crop_id,
                "field_id":        entry.field_id,
                "field_location":  field.location       if field else user_location,
                "field_moisture":  field.moisture_level if field else None,
                "field_ph":        field.ph_level       if field else None,
                "growth_stage_id": entry.growth_stage_id,
                "week_events":     original_events,
                "sowing_window":   sowing_window,
                "irrigation_period": irrigation_period,
                "seasonal_entry_id": seasonal_entry.id if seasonal_entry else None,
            })

        updated_plan = RuleEngine.update_weekly_plan(
            raw_entries, plan.week_start_date, plan.week_end_date, as_of_date
        )

        updated_by_crop = {item["crop_id"]: item for item in updated_plan}
        for entry in plan.entries:
            updated = updated_by_crop.get(entry.crop_id)
            if not updated:
                continue
            WeeklyPlanEntryRepository.update(entry, {
                "week_events":         json.dumps(updated["week_events"]),
                "climate_adjustments": json.dumps(updated.get("climate_adjustments_made", [])),
            })

        # Record permanent one-time event shifts in the actual-dates layer.
        PlanOverrideService.sync_forecast_shifts(user_id, as_of_date, updated_plan)

        # No suitable sowing day left, or the window passed without completion →
        # ask the farmer (on the day it happens). A "decision needed" that the
        # forecast reverses gets one short follow-up.
        for item in updated_plan:
            if notify and item.get("seasonal_entry_id"):
                WeeklyPlannerService._notify_sowing_decision(user_id, item)

        return Status.SUCCESS

    SOWING_DAY_APPEARED_TEXT = "A suitable sowing day appeared"

    @staticmethod
    def _notify_sowing_decision(user_id: int, item: dict) -> None:
        """Sowing decision notifications for one seasonal plan entry (fixed texts, no AI).

        - decision needed / overdue: a warning, unless the latest sowing notification
          for this entry already asks for a decision (not repeated every day).
        - decision needed reversed (a suitable day appeared, sowing scheduled again):
          "A suitable sowing day appeared: sow on <date>", once per reversal.
        """
        from app.models.notification import Notification
        from app.repositories.notification_repository import NotificationRepository

        status = item.get("sowing_status")
        entry_id = item["seasonal_entry_id"]
        decision_texts = (RuleEngine.SOWING_OVERDUE_TEXT, RuleEngine.SOWING_DECISION_TEXT)
        appeared = WeeklyPlannerService.SOWING_DAY_APPEARED_TEXT
        latest = (Notification.query
                  .filter(Notification.user_id == user_id,
                          Notification.entity_type == "seasonal_plan_entry",
                          Notification.entity_id == entry_id,
                          db.or_(Notification.message.in_(decision_texts),
                                 Notification.message.like(f"{appeared}%")))
                  .order_by(Notification.id.desc()).first())
        latest_is_decision = bool(latest and latest.message in decision_texts)
        crop_obj = rule_base_service.get_crop_by_id(item["crop_id"])
        crop = crop_obj.name if crop_obj else f"Crop {item['crop_id']}"
        base = {"user_id": user_id, "entity_type": "seasonal_plan_entry", "entity_id": entry_id}

        if status in RuleEngine.NO_SOWING_STATUSES:
            if latest_is_decision:
                return
            window = item.get("sowing_window") or {}
            overdue = status == "overdue"
            text = RuleEngine.SOWING_OVERDUE_TEXT if overdue else RuleEngine.SOWING_DECISION_TEXT
            what = ("has passed and sowing was not recorded as done" if overdue
                    else "has no suitable sowing day left in the forecast")
            NotificationRepository.create({
                **base,
                "title":             f"{text} – {crop}",
                "message":           text,
                "detail":            (f"{crop}: the sowing window ({window.get('planned')} – {window.get('end')}) "
                                      f"{what}. Options: "
                                      f"{RuleEngine.SOWING_OVERDUE_OPTIONS}. The system does not choose."),
                "notification_type": "warning",
            })
            return

        sowing = next((e["date"] for e in item.get("week_events", []) if e["event_type"] == "sowing"), None)
        if (status in ("planned", "window_set") and sowing
                and latest and latest.message == RuleEngine.SOWING_DECISION_TEXT):
            d = date.fromisoformat(sowing)
            text = f"{appeared}: sow on {d.day} {d.strftime('%b')}"
            NotificationRepository.create({
                **base,
                "title":             f"{appeared} – {crop}",
                "message":           text,
                "detail":            f"{crop}: {text}. The earlier 'decision needed' no longer applies.",
                "notification_type": "info",
            })

    @staticmethod
    def delete(plan_id: int):
        plan = WeeklyPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        WeeklyPlanRepository.delete(plan)   # cascades to entries
        return plan
