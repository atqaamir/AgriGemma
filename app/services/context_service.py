# app/services/context_service.py
from app.services.domain_service.field_service import FieldService
from app.services.domain_service.crop_service import CropService
from app.services.seasonal_planner_service import SeasonalPlannerService
from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.services.domain_service.task_service import TaskService


class ContextService:

    @staticmethod
    def get_context(field_id: int, crop_id: int) -> dict:
        """
        Build the current operational context for a field/crop.

        This service aggregates the current farm state required
        by planners, advisors, chatbot flows, and update systems.
        """

        field = FieldService.get_field_by_id(field_id)

        crop = CropService.get_crop_by_id(crop_id)

        seasonal_plan = SeasonalPlannerService.get_active_plan(
            field_id=field_id
        )

        weekly_plan = WeeklyPlannerService.get_active_weekly_plan(
            field_id=field_id
        )

        today_tasks = TaskService.get_today_tasks(
            field_id=field_id
        )

        current_phase = ContextService._determine_current_phase(
            seasonal_plan=seasonal_plan,
            weekly_plan=weekly_plan
        )

        return {
            "field": field,
            "crop": crop,

            "seasonal_plan": seasonal_plan,
            "weekly_plan": weekly_plan,

            "today_tasks": today_tasks,

            "current_phase": current_phase,
        }

    @staticmethod
    def _determine_current_phase(
        seasonal_plan: dict,
        weekly_plan: dict
    ) -> str:
        """
        Determine current operational farming phase.

        For MVP:
        Prefer weekly plan phase if available.
        """

        if weekly_plan and weekly_plan.get("phase"):
            return weekly_plan["phase"]

        return "unknown"