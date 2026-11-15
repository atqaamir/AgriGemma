from datetime import date
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.services.task_generation_service import TaskGenerationService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.utils import enums_


class PlanningAgent:
    @staticmethod
    def generate_weekly_plan(user_id: int, tag: str = "", week_start_date: date = None) -> str:
        plan = WeeklyPlannerService.generate_plan(user_id, week_start_date)
        return enums_.Status.SUCCESS if plan else enums_.Status.FAILED

    @staticmethod
    def generate_daily_tasks(user_id: int, tag: str = "") -> str:
        result = TaskGenerationService().generate_daily_tasks(user_id=user_id)
        return enums_.Status.SUCCESS if result and isinstance(result, dict) else enums_.Status.FAILED

    @staticmethod
    def generate_seasonal_plan(user_id: int, tag: str = "") -> str:
        plan = SeasonalPlannerService.auto_generate_plan(user_id)
        return enums_.Status.SUCCESS if plan else enums_.Status.FAILED

    @staticmethod
    def apply_forecast(user_id: int, as_of_date=None) -> str:
        """Forecast re-plan of the active weekly plan (runs on every daily update)."""
        result = WeeklyPlannerService.update_plan(user_id, as_of_date)
        return enums_.Status.SUCCESS if result == enums_.Status.SUCCESS else enums_.Status.FAILED

    @staticmethod
    def daily_update(user_id: int, as_of_date=None, tag: str = "") -> str:
        """Impact-specific follow-up after the forecast re-plan (which the coordinator
        already ran via apply_forecast): task updates when today's tasks are impacted."""
        if tag == "impact_tasks":
            from app.services.task_update_service import TaskUpdateService
            TaskUpdateService.update_tasks(user_id, as_of_date)
        return enums_.Status.SUCCESS
