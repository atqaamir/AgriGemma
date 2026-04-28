from app.services.weather_service.weekly_planner_service import WeeklyPlannerService
from app.services.task_generation_service import TaskGenerationService
from app.services.weekly_planning_service.weekly_update_service import TaskUpdateService



class PlanningAgent:
    @staticmethod
    def generate_weekly_plan(self,field_id: str, context: dict) -> dict:
        return WeeklyPlannerService().generate_weekly_plan(
            field_id=field_id,
            seasonal_plan=context["seasonal_plan"],
            crop=context["crop"],
        )

    @staticmethod
    def generate_daily_tasks(self, field_id: str, weekly_plan: dict) -> list:
        return TaskGenerationService().generate_daily_tasks(
            field_id=field_id,
            weekly_plan=weekly_plan,
        )

    @staticmethod
    def evaluate_daily_update(self,field_id: str, context: dict, risk_context: dict) -> dict:

        return TaskUpdateService().evaluate_daily_update(
                field_id=field_id,
            seasonal_plan=context["seasonal_plan"],
            weekly_plan=context["weekly_plan"],
            daily_forecast=risk_context["daily_forecast"],
            weekly_forecast=risk_context["weekly_forecast"],
            soil_condition=risk_context["soil_condition"],
            crop_health=risk_context["crop_health"],
        )

