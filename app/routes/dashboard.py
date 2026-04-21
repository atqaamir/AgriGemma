from flask import Blueprint, jsonify, render_template, request
from app.services.dashboard_service import build_dashboard_data, chat_with_advisor, generate_seasonal_plan

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
def dashboard_page():
    return render_template("dashboard.html")


@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    dashboard_data = build_dashboard_data()
    return jsonify(dashboard_data), 200 

@dashboard_bp.route("/<int:user_id>/advisor", methods=["GET"])
def get_advisor(user_id):
    user_message = request.args.get("message", "")
    if not user_message:
        return jsonify({"error": "Message parameter is required"}), 400

    response = chat_with_advisor(user_id=user_id, message=user_message)
    return jsonify({"response": response}), 200
    
@dashboard_bp.route("/<int:user_id>/seasonal-plan", methods=["GET"])
def get_seasonal_plan(user_id):
    plan = generate_seasonal_plan(user_id=user_id)
    return jsonify(plan), 200