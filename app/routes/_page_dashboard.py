from flask import Blueprint, jsonify, render_template, request
from app.services.dashboard_service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
def dashboard_page():
    print("Rendering dashboard page")
    return render_template("dashboard.html")


@dashboard_bp.route("/<int:user_id>/dashboard")
def get_dashboard(user_id):
    dashboard_data = DashboardService.build_dashboard_data(user_id)
    return jsonify(dashboard_data), 200


@dashboard_bp.route("/<int:user_id>/dashboard/generate-summary", methods=["POST"])
def generate_summary(user_id):
    result = DashboardService.generate_and_store_summary(user_id)
    return jsonify(result), 200

@dashboard_bp.route("/<int:user_id>/advisor", methods=["GET"])
def get_advisor(user_id):
    user_message = request.args.get("message", "")
    if not user_message:
        return jsonify({"error": "Message parameter is required"}), 400

    response = DashboardService().chat_with_advisor(user_id=user_id, message=user_message)
    return jsonify({"response": response}), 200
    
@dashboard_bp.route("/<int:user_id>/seasonal-plan", methods=["GET"])
def get_seasonal_plan(user_id):
    plan = DashboardService().generate_seasonal_plan(user_id=user_id)
    return jsonify(plan), 200