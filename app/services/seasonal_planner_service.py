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
            crop_name  = rule_base_service.get_crop_by_id(entry.crop_id).name
            soil_name  = (
                rule_base_service.get_soil_by_id(entry.soil_type_id).name
                if entry.soil_type_id else None
            )
            water_name = (
                rule_base_service.get_water_source_by_id(entry.water_source_id).name
                if entry.water_source_id else None
            )

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
                "schedule":     schedule,
                "adjustments":  adjustments,
            })

        return {
            "plan_id":          plan.id,
            "growth_stage":     growth_stage,
            "currently_active": plan.currently_active,
            "total_crops":      len(crops_output),
            "crops":            crops_output,
        }

    # ------------------------------------------------------------------ #
    #  Plan generation
    # ------------------------------------------------------------------ #

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
                "crop_id":               rule_base_service.get_crop_by_name(adjusted_plan["crop"]).id,
                "soil_type_id":          rule_base_service.get_soil_by_name(adjusted_plan["soil_type"]).id,
                "water_source_id":       rule_base_service.get_water_source_by_name(adjusted_plan["water_source"]).id,
                "sowing":                adjusted_plan["sowing"],
                "harvesting":            adjusted_plan["harvesting"],
                "irrigation_start_date": adjusted_plan["irrigation_start_date"],
                "irrigation_frequency":  adjusted_plan["irrigation_frequency"],
                "fertilization_date":    adjusted_plan["fertilization_date"],
                "adjustments_to_make":   json.dumps(adjusted_plan["adjustments_to_make"]),
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
        field_id             : int

        Returns
        -------
        Updated SeasonalPlanEntry ORM object, or None if not found.
        """
        entry = SeasonalPlanEntryRepository.get_by_id(entry_id)
        if not entry:
            return None

        DIRECT_FIELDS  = {
            "irrigation_start_date", "irrigation_frequency",
            "fertilization_date", "harvesting", "field_id",
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
    def generate_adjustment_reasoning(plan_data: dict) -> str:
        """Call Ollama (fast_complete) to produce a one-paragraph plain-English
        explanation of why the plan's adjustments are needed. Returns a fallback
        string if the AI call fails."""
        from app.services.ai_model_service.ai_model_service import fast_complete

        infeasible = [c for c in plan_data.get("crops", []) if not c.get("feasible")]
        feasible   = [c for c in plan_data.get("crops", []) if c.get("feasible")]

        if not infeasible:
            crop_names = ", ".join(c["crop"] for c in feasible)
            return (
                f"All recommended crops ({crop_names}) are fully compatible with your soil "
                "and water conditions. No corrective adjustments are required."
            )

        lines = []
        for crop in plan_data.get("crops", []):
            if crop.get("adjustments"):
                lines.append(f"{crop['crop']} ({crop['soil_type']} soil, {crop['water_source']} water): "
                             + "; ".join(crop["adjustments"]))

        adjustments_text = "\n".join(lines) if lines else "No specific adjustments recorded."

        prompt = (
            "You are an agricultural advisor. In 2–3 sentences explain to a farmer "
            "why the following crop adjustments are necessary, focusing on soil and water compatibility risks.\n\n"
            f"Growth stage: {plan_data.get('growth_stage', 'unknown')}\n"
            f"Adjustments:\n{adjustments_text}\n\n"
            "Write a clear, practical explanation. Do not use bullet points or headers."
        )

        try:
            raw = fast_complete(prompt)
            if isinstance(raw, dict):
                text = raw.get("response") or raw.get("text") or raw.get("output") or ""
            else:
                text = str(raw)
            text = text.strip()
            return text if text else SeasonalPlannerService._adjustment_reasoning_fallback(plan_data)
        except Exception as exc:
            logger.warning("AI adjustment reasoning failed: %s", exc)
            return SeasonalPlannerService._adjustment_reasoning_fallback(plan_data)

    @staticmethod
    def _adjustment_reasoning_fallback(plan_data: dict) -> str:
        infeasible = [c["crop"] for c in plan_data.get("crops", []) if not c.get("feasible")]
        feasible   = [c["crop"] for c in plan_data.get("crops", []) if c.get("feasible")]
        parts = []
        if infeasible:
            parts.append(
                f"{', '.join(infeasible)} cannot be grown as-is due to soil and water source incompatibilities."
            )
        if feasible:
            parts.append(
                f"{', '.join(feasible)} can proceed with the adjusted schedule shown in the timeline."
            )
        parts.append(
            "Review each crop's required changes before finalising your seasonal plan."
        )
        return " ".join(parts)
