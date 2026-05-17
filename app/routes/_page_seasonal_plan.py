from datetime import date

from flask import Blueprint, render_template, jsonify

from app.services.seasonal_planner_service import SeasonalPlannerService

seasonal_plan_bp = Blueprint("seasonal_plan", __name__)


@seasonal_plan_bp.route("/<int:user_id>/seasonal-plan-page", methods=["GET"])
def seasonal_plan_page(user_id):
    plan = SeasonalPlannerService.show_active_plan(user_id)
    return render_template(
        "seasonal_plan.html",
        plan=plan,
        today_str=date.today().isoformat(),
    )


@seasonal_plan_bp.route("/<int:user_id>/seasonal-plan-data", methods=["GET"])
def seasonal_plan_data(user_id):
    plan = SeasonalPlannerService.show_active_plan(user_id)
    return jsonify(plan), 200


@seasonal_plan_bp.route("/<int:user_id>/seasonal-plan-reasoning/<crop_name>", methods=["GET"])
def seasonal_plan_reasoning(user_id, crop_name):
    explanation = SeasonalPlannerService.get_crop_explanation(user_id, crop_name)
    return jsonify({"explanation": explanation}), 200
