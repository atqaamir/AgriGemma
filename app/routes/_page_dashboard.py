import threading
from flask import Blueprint, current_app, jsonify, render_template
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
    app = current_app._get_current_object()
    def _bg():
        with app.app_context():
            DashboardService.generate_and_store_summary(user_id)
    threading.Thread(target=_bg, daemon=False).start()
    return jsonify({"status": "generating"}), 202

