from flask import Blueprint, jsonify, request
from app.services.dashboard_service import build_dashboard_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    location = request.args.get("location", "Lahore")
    crop_name = request.args.get("crop", "Wheat")
    field_name = request.args.get("field", "North Field")

    dashboard_data = build_dashboard_data(
        location=location,
        crop_name=crop_name,
        field_name=field_name
    )

    return jsonify(dashboard_data), 200