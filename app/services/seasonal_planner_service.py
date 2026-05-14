import json

from app.rules.rule_engine.rule_engine import RuleEngine
from app.repositories.seasonal_plan_repository import SeasonalPlanRepository
from app.services.rule_base_service import rule_base_service


class SeasonalPlannerService:

    # ------------------------------------------------------------------ #
    #  Plan generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_initial_plan(user_id: int, crop: str, soil_type: str,
                              water_source: str, growth_stage: str = "Seedling"):
        initial_plan  = RuleEngine.generate_initial_plan(crop, soil_type, water_source, growth_stage)
        adjusted_plan = RuleEngine.adjust_initial_plan(initial_plan)

        # Replace name strings with vocabulary IDs for storage
        adjusted_plan["crop_id"]         = rule_base_service.get_crop_by_name(adjusted_plan.pop("crop")).id
        adjusted_plan["soil_type_id"]    = rule_base_service.get_soil_by_name(adjusted_plan.pop("soil_type")).id
        adjusted_plan["water_source_id"] = rule_base_service.get_water_source_by_name(adjusted_plan.pop("water_source")).id
        adjusted_plan["growth_stage_id"] = rule_base_service.get_stage_by_name(adjusted_plan.pop("growth_stage")).id

        adjusted_plan["user_id"]             = user_id
        adjusted_plan["currently_active"]    = True
        adjusted_plan["adjustments_to_make"] = json.dumps(adjusted_plan["adjustments_to_make"])

        return SeasonalPlanRepository.create(adjusted_plan)

    # ------------------------------------------------------------------ #
    #  Read
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_active_plan(user_id: int):
        return SeasonalPlanRepository.get_active_by_user_id(user_id)

    @staticmethod
    def get_all_plans(user_id: int):
        return SeasonalPlanRepository.get_by_user_id(user_id)

    # ------------------------------------------------------------------ #
    #  Update  (only currently_active may be changed)
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_plan(plan_id: int, data: dict):
        plan = SeasonalPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        allowed = {k: v for k, v in data.items() if k == "currently_active"}
        return SeasonalPlanRepository.update(plan, allowed)

    # ------------------------------------------------------------------ #
    #  Delete
    # ------------------------------------------------------------------ #

    @staticmethod
    def delete(plan_id: int):
        plan = SeasonalPlanRepository.get_by_id(plan_id)
        if not plan:
            return None
        SeasonalPlanRepository.delete(plan)
        return plan
