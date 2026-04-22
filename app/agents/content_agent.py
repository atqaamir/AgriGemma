from app.services.field_service import field_service
from app.services.crop_service import crop_service
from app.services.seasonal_planner_service import seasonal_planner_service
from app.services.weekly_planner_service import weekly_planner_service


class ContextAgent:
    @staticmethod
    def get_context(field_id: str) -> dict:
        field_data = field_service.get_field_summary(field_id)
        crop_data = crop_service.get_active_crop_for_field(field_id)
        seasonal_plan = seasonal_planner_service.get_active_plan(field_id)
        weekly_plan = weekly_planner_service.get_active_weekly_plan(field_id)

        return {
            "field": field_data,
            "crop": crop_data,
            "seasonal_plan": seasonal_plan,
            "weekly_plan": weekly_plan,
        }