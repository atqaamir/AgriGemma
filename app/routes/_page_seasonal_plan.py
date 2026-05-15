from datetime import date

from flask import Blueprint, render_template, jsonify

from app.services.seasonal_planner_service import SeasonalPlannerService

seasonal_plan_bp = Blueprint("seasonal_plan", __name__)


@seasonal_plan_bp.route("/<int:user_id>/seasonal-plan-page", methods=["GET"])
def seasonal_plan_page(user_id):
    plan = SeasonalPlannerService.show_active_plan(user_id)

    if "status" in plan and plan["status"] in ("no_plan", "no_active_plan"):
        ai_reasoning = "No active seasonal plan found."
    else:
        ai_reasoning = SeasonalPlannerService.generate_adjustment_reasoning(plan)

    return render_template(
        "seasonal_plan.html",
        plan=plan,
        ai_reasoning=ai_reasoning,
        today_str=date.today().isoformat(),   # "YYYY-MM-DD" used by JS to find current phase
    )


@seasonal_plan_bp.route("/<int:user_id>/seasonal-plan-data", methods=["GET"])
def seasonal_plan_data(user_id):
    plan = SeasonalPlannerService.show_active_plan(user_id)
    if "status" not in plan:
        plan["ai_reasoning"] = SeasonalPlannerService.generate_adjustment_reasoning(plan)
    return jsonify(plan), 200
