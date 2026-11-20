from datetime import date

from flask import Blueprint, render_template

from app.services.weekly_planning_service.weekly_planner_service import WeeklyPlannerService
from app.utils import clock

weekly_plan_bp = Blueprint("weekly_plan", __name__)


@weekly_plan_bp.route("/<int:user_id>/weekly-plan-page", methods=["GET"])
def weekly_plan_page(user_id):
    plan = WeeklyPlannerService.show_active_plan(user_id)
    return render_template(
        "weekly_plan.html",
        plan=plan,
        user_id=user_id,
        today_str=clock.today().isoformat(),
    )
