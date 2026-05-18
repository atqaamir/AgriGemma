from datetime import date
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.services.task_generation_service import TaskGenerationService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.utils import enums_


class PlanningAgent:
    @staticmethod
    def generate_weekly_plan(user_id: int, tag: str = "") -> str:
        plan = WeeklyPlannerService.generate_plan(user_id)
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
    def daily_update(user_id: int, as_of_date=None, tag: str = "") -> str:
        if tag == "impact_weekly":
            result = WeeklyPlannerService.update_plan(user_id, as_of_date)
            return enums_.Status.SUCCESS if result == enums_.Status.SUCCESS else enums_.Status.FAILED

        if tag == "impact_tasks":
            from app.services.task_update_service import TaskUpdateService
            plan_result = WeeklyPlannerService.update_plan(user_id, as_of_date)
            TaskUpdateService.update_tasks(user_id, as_of_date)
            return enums_.Status.SUCCESS if plan_result == enums_.Status.SUCCESS else enums_.Status.FAILED

        return enums_.Status.SUCCESS
