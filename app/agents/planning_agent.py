from app.services.weekly_planner_service import weekly_planner_service
from app.services.task_generation_service import task_generation_service
from app.services.task_update_service import task_update_service
from app.services.plan_revision_service import plan_revision_service


class PlanningAgent:
    @staticmethod
    def generate_weekly_plan(field_id: str, context: dict) -> dict:
        return weekly_planner_service.generate_weekly_plan(
            field_id=field_id,
            seasonal_plan=context["seasonal_plan"],
            crop=context["crop"],
        )

    @staticmethod
    def generate_daily_tasks(field_id: str, weekly_plan: dict) -> list:
        return task_generation_service.generate_daily_tasks(
            field_id=field_id,
            weekly_plan=weekly_plan,
        )

    @staticmethod
    def evaluate_daily_update(field_id: str, context: dict, risk_context: dict) -> dict:
        return task_update_service.evaluate_daily_update(
            field_id=field_id,
            seasonal_plan=context["seasonal_plan"],
            weekly_plan=context["weekly_plan"],
            daily_forecast=risk_context["daily_forecast"],
            weekly_forecast=risk_context["weekly_forecast"],
            soil_condition=risk_context["soil_condition"],
            crop_health=risk_context["crop_health"],
        )

    @staticmethod
    def create_proposed_revision(field_id: str, update_result: dict) -> dict:
        return plan_revision_service.create_proposed_revision(
            field_id=field_id,
            update_result=update_result,
        )