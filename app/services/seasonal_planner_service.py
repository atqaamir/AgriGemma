import json
import logging
from datetime import datetime

from app.rules.rule_engine.rule_engine import RuleEngine
from app.repositories.seasonal_plan_repository import SeasonalPlanRepository, SeasonalPlanEntryRepository
from app.services.rule_base_service import rule_base_service

logger = logging.getLogger(__name__)


class SeasonalPlannerService:

    # ------------------------------------------------------------------ #
    #  Internal formatter
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_plan(plan) -> dict:
        """Convert a SeasonalPlan ORM object (with its entries) into a
        clean, frontend-ready dict. All IDs are resolved to human-readable
        names; dates stay as MM/DD/YYYY strings."""

        if plan is None:
            return {
                "status":  "no_plan",
                "message": "No seasonal plan found.",
            }

        growth_stage = (
            rule_base_service.get_stage_by_id(plan.growth_stage_id).name
            if plan.growth_stage_id else None
        )

        crops_output = []
        for entry in plan.entries:
            crop_name  = entry.crop_name_rel.name if entry.crop_name_rel else None
            soil_name  = entry.soil_rel.name      if entry.soil_rel      else None
            water_name = entry.water_rel.name     if entry.water_rel     else None

            adjustments = json.loads(entry.adjustments_to_make) if entry.adjustments_to_make else []
            feasible    = entry.sowing is not None   # avoid action nullifies sowing

            schedule = (
                {
                    "sowing_date":           entry.sowing,
                    "harvesting_date":       entry.harvesting,
                    "irrigation_start_date": entry.irrigation_start_date,
                    "irrigation_frequency":  (
                        f"{entry.irrigation_frequency} times per week"
                        if entry.irrigation_frequency is not None else None
                    ),
                    "fertilization_date":    entry.fertilization_date,
                }
                if feasible else None
            )

            crops_output.append({
                "crop":         crop_name,
                "soil_type":    soil_name,
                "water_source": water_name,
                "feasible":     feasible,
                "feasibility":  entry.feasibility,
                "schedule":     schedule,
                "adjustments":  adjustments,
            })

        last_updated = None
        if plan.last_updated:
            d = plan.last_updated
            last_updated = f"{d.day} {d.strftime('%B')} {d.year}" if hasattr(d, 'strftime') else str(d)

        return {
            "plan_id":          plan.id,
            "growth_stage":     growth_stage,
            "currently_active": plan.currently_active,
            "total_crops":      len(crops_output),
            "last_updated":     last_updated,
            "crops":            crops_output,
        }

    # ------------------------------------------------------------------ #
    #  Plan generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def auto_generate_plan(user_id: int, growth_stage: str = "Sowing") -> object:
        """Auto-generate a seasonal plan from the user's active fields and crops.
        
        Reads the user's fields, extracts their soil types and water sources,
        and generates one seasonal plan entry per active crop in each field.
        """
        from app.services.domain_service.field_service import FieldService
        
        # Get all active fields for this user
        fields = FieldService.get_fields_by_user(user_id)
        active_fields = [f for f in fields if f.currently_active]
        
        if not active_fields:
            return None
        
        # Build crop list from fields: one entry per active crop per field
        crops = []
        for field in active_fields:
            # Get the active crop(s) in this field
            active_crops = [c for c in field.crops if c.currently_active] if field.crops else []

            for crop in active_crops:
                crops.append({
                    "crop": crop.crop_name_rel.name if crop.crop_name_rel else crop.crop_name,
                    "soil_type": field.soil_type_name,
                    "water_source": field.water_source_name,
                })
        
        if not crops:
            return None
        
        return SeasonalPlannerService.generate_plan(user_id, growth_stage, crops)

    @staticmethod
    def generate_plan(user_id: int, growth_stage: str, crops: list) -> object:
        """Create a seasonal plan with one entry per crop.

        Each item in `crops` must be a dict with keys:
            crop, soil_type, water_source
        growth_stage is shared across all crop entries.
        """
        growth_stage_id = rule_base_service.get_stage_by_name(growth_stage).id

        # Create the parent plan record
        plan = SeasonalPlanRepository.create({
            "user_id":          user_id,
            "growth_stage_id":  growth_stage_id,
            "currently_active": True,
        })

        # Generate, adjust, and persist one entry per crop
        for crop_input in crops:
            crop         = crop_input["crop"]
            soil_type    = crop_input["soil_type"]
            water_source = crop_input["water_source"]

            initial_plan  = RuleEngine.generate_initial_plan(crop, soil_type, water_source, growth_stage)
            adjusted_plan = RuleEngine.adjust_initial_plan(initial_plan)

            entry_data = {
                "plan_id":               plan.id,
                "crop_name_id":          rule_base_service.get_crop_by_name(adjusted_plan["crop"]).id,
                "soil_id":               rule_base_service.get_soil_by_name(adjusted_plan["soil_type"]).id,
                "water_source_id":       rule_base_service.get_water_source_by_name(adjusted_plan["water_source"]).id,
                "growth_id":             growth_stage_id,
                "sowing":                adjusted_plan["sowing"],
                "harvesting":            adjusted_plan["harvesting"],
                "irrigation_start_date": adjusted_plan["irrigation_start_date"],
                "irrigation_frequency":  adjusted_plan["irrigation_frequency"],
                "fertilization_date":    adjusted_plan["fertilization_date"],
                "adjustments_to_make":   json.dumps(adjusted_plan["adjustments_to_make"]),
                "feasibility":           adjusted_plan.get("feasibility", "Ideal"),
            }
            SeasonalPlanEntryRepository.create(entry_data)

        return plan

    # ------------------------------------------------------------------ #
    #  Read (raw ORM objects)
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_active_plan(user_id: int):
        return SeasonalPlanRepository.get_active_by_user_id(user_id)

    @staticmethod
    def get_all_plans(user_id: int):
        return SeasonalPlanRepository.get_by_user_id(user_id)

    @staticmethod
    def get_plan_entries(plan_id: int):
        return SeasonalPlanEntryRepository.get_by_plan_id(plan_id)

    # ------------------------------------------------------------------ #
    #  Read (formatted for frontend)
    # ------------------------------------------------------------------ #

    @staticmethod
    def show_active_plan(user_id: int) -> dict:
        """Return the user's active plan formatted for the UI.

        Example response
        ----------------
        {
          "plan_id": 1,
          "growth_stage": "Seedling",
          "currently_active": true,
          "total_crops": 3,
          "crops": [
            {
              "crop": "Maize",
              "soil_type": "Loamy",
              "water_source": "Groundwater",
              "feasible": true,
              "schedule": {
                "sowing_date": "07/12/2026",
                "harvesting_date": "12/04/2026",
                "irrigation_start_date": "07/22/2026",
                "irrigation_frequency": "3 times per week",
                "fertilization_date": "08/11/2026"
              },
              "adjustments": []
            },
            {
              "crop": "Rice",
              "soil_type": "Clay",
              "water_source": "Recycled",
              "feasible": false,
              "schedule": null,
              "adjustments": [
                "Rice is extremely incompatible with Recycled water source - please consider a different field or a different crop"
              ]
            }
          ]
        }
        """
        plan = SeasonalPlanRepository.get_active_by_user_id(user_id)
        if plan is None:
            return {
                "status":  "no_active_plan",
                "message": "No active seasonal plan found for this user.",
            }
        return SeasonalPlannerService._format_plan(plan)

    @staticmethod
    def show_plan(plan_id: int) -> dict:
        """Return any plan (active or inactive) formatted for the UI."""
        plan = SeasonalPlanRepository.get_by_id(plan_id)
        return SeasonalPlannerService._format_plan(plan)

    @staticmethod
    def show_all_plans(user_id: int) -> list:
        """Return all plans for a user, each formatted for the UI."""
        plans = SeasonalPlanRepository.get_by_user_id(user_id)
        return [SeasonalPlannerService._format_plan(p) for p in plans]

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_plan(plan_id: int, data: dict):
        """Update plan-level fields.

        Allowed keys
        ------------
        currently_active : bool
        growth_stage_id  : int
        """
        plan = SeasonalPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        allowed_keys = {"currently_active", "growth_stage_id"}
        allowed = {k: v for k, v in data.items() if k in allowed_keys}
        return SeasonalPlanRepository.update(plan, allowed)

    @staticmethod
    def update_entry(entry_id: int, data: dict):
        """Update a SeasonalPlanEntry.

        Allowed keys
        ------------
        sowing               : "MM/DD/YYYY"
            When sowing changes, the delta (new − old) is automatically
            cascaded to irrigation_start_date, fertilization_date, and
            harvesting — unless those fields are also explicitly supplied
            in ``data``, in which case the explicit value wins.
        irrigation_start_date: "MM/DD/YYYY"  — direct override
        irrigation_frequency : int           — times per week
        fertilization_date   : "MM/DD/YYYY"  — direct override
        harvesting           : "MM/DD/YYYY"  — direct override

        Returns
        -------
        Updated SeasonalPlanEntry ORM object, or None if not found.
        """
        entry = SeasonalPlanEntryRepository.get_by_id(entry_id)
        if not entry:
            return None

        DIRECT_FIELDS  = {
            "irrigation_start_date", "irrigation_frequency",
            "fertilization_date", "harvesting",
        }
        CASCADE_FIELDS = ("irrigation_start_date", "fertilization_date", "harvesting")

        def _parse(s):
            if not s:
                return None
            return datetime.strptime(s, "%m/%d/%Y").date()

        def _fmt(d):
            return d.strftime("%m/%d/%Y")

        updates = {}

        # ── Sowing change → cascade delta to dependent dates ──────────────
        if "sowing" in data:
            new_sowing = _parse(data["sowing"])
            old_sowing = _parse(entry.sowing)

            if new_sowing and old_sowing and new_sowing != old_sowing:
                delta = new_sowing - old_sowing
                for field in CASCADE_FIELDS:
                    if field not in data:          # explicit override takes priority
                        old_val = _parse(getattr(entry, field))
                        if old_val:
                            updates[field] = _fmt(old_val + delta)

            updates["sowing"] = data["sowing"]

        # ── Remaining direct fields ────────────────────────────────────────
        for key in DIRECT_FIELDS:
            if key in data:
                updates[key] = data[key]

        if not updates:
            return entry

        return SeasonalPlanEntryRepository.update(entry, updates)

    # ------------------------------------------------------------------ #
    #  Delete
    # ------------------------------------------------------------------ #

    @staticmethod
    def delete(plan_id: int):
        plan = SeasonalPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        SeasonalPlanRepository.delete(plan)   # cascades to entries via relationship
        return plan

    # ------------------------------------------------------------------ #
    #  AI reasoning
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_adjustment_reasoning(plan_data: dict) -> dict:
        """Return a dict { crop_name: explanation } for every Not Feasible crop.

        Checks seasonal_plan.ai_explanation (JSON) first. Only calls the AI for
        crops that don't have a stored explanation yet, then persists the result.
        Returns an empty dict when there are no Not Feasible crops.
        """
        from app.services.ai_model_service.ai_model_service import fast_complete
        from app.extensions import db

        not_feasible = [c for c in plan_data.get("crops", []) if c.get("feasibility") == "Not Feasible"]
        if not not_feasible:
            return {}

        # Load any already-stored explanations from the plan row
        plan_obj = SeasonalPlanRepository.get_by_id(plan_data.get("plan_id"))
        stored: dict = {}
        if plan_obj and plan_obj.ai_explanation:
            try:
                stored = json.loads(plan_obj.ai_explanation)
            except (json.JSONDecodeError, TypeError):
                stored = {}

        updated = False
        for crop in not_feasible:
            crop_name = crop["crop"]
            if crop_name in stored:
                continue  # already cached

            adjustments = crop.get("adjustments") or []
            adj_text    = "; ".join(adjustments) if adjustments else "incompatible soil or water conditions"

            prompt = (
                "You are an agricultural advisor. In 2–3 sentences explain to a farmer "
                f"why {crop_name} cannot be grown under current conditions "
                f"({crop.get('soil_type', '')} soil, {crop.get('water_source', '')} water), "
                f"focusing on: {adj_text}. "
                "Write clearly and practically. No bullet points or headers."
            )

            try:
                raw  = fast_complete(prompt)
                text = (raw.get("response") or raw.get("text") or raw.get("output") or "") \
                    if isinstance(raw, dict) else str(raw)
                text = text.strip()
                stored[crop_name] = text if text else SeasonalPlannerService._adjustment_reasoning_fallback(crop_name, adjustments)
            except Exception as exc:
                logger.warning("AI adjustment reasoning failed for %s: %s", crop_name, exc)
                stored[crop_name] = SeasonalPlannerService._adjustment_reasoning_fallback(crop_name, adjustments)

            updated = True

        if updated and plan_obj:
            plan_obj.ai_explanation = json.dumps(stored)
            db.session.commit()

        return stored

    @staticmethod
    def get_crop_explanation(user_id: int, crop_name: str) -> str:
        """Return the AI explanation for a single Not Feasible crop.
        Generates and caches via generate_adjustment_reasoning if not yet stored."""
        plan = SeasonalPlanRepository.get_active_by_user_id(user_id)
        if not plan:
            return ""
        plan_data    = SeasonalPlannerService._format_plan(plan)
        explanations = SeasonalPlannerService.generate_adjustment_reasoning(plan_data)
        return explanations.get(crop_name, "")

    @staticmethod
    def _adjustment_reasoning_fallback(crop_name: str, adjustments: list) -> str:
        reason = "; ".join(adjustments) if adjustments else "incompatible soil or water conditions"
        return (
            f"{crop_name} cannot be grown as-is: {reason}. "
            "Review the required changes before finalising your seasonal plan."
        )
