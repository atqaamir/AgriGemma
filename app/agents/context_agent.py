from app.services.field_service import FieldService
from app.services.crop_service import CropService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planner_service import WeeklyPlannerService


class ContextAgent:
    @staticmethod
    def get_context(crop_id: str, field_id: str) -> dict:
        field_data = FieldService().get_field_summary(field_id)
        crop = CropService().get_crop_by_id(crop_id)
        seasonal_plan = SeasonalPlannerService().get_active_plan( field_id)
        weekly_plan = WeeklyPlannerService().get_active_weekly_plan(field_id)

        return {
            "field": field_data,
            "crop": crop,
            "seasonal_plan": seasonal_plan,
            "weekly_plan": weekly_plan,
        }