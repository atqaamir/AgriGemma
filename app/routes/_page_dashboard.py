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


# ── Farm report (one AI call on "Generate report") ───────────────────────────

_report_running: set[int] = set()
_report_lock = threading.Lock()


@dashboard_bp.route("/<int:user_id>/farm-report", methods=["GET"])
def get_farm_report(user_id):
    """Latest stored farm report + whether the farm changed since. No AI call."""
    from app.services import insight_report_service as reports
    with _report_lock:
        running = user_id in _report_running
    return jsonify({"report": reports.payload(user_id, "farm_report"), "generating": running}), 200


@dashboard_bp.route("/<int:user_id>/farm-report/generate", methods=["POST"])
def generate_farm_report(user_id):
    """Run the one AI call in the background; poll GET /<user_id>/farm-report."""
    from app.services import farm_report_service
    with _report_lock:
        if user_id in _report_running:
            return jsonify({"status": "already generating"}), 202
        _report_running.add(user_id)
    app = current_app._get_current_object()

    def _bg():
        try:
            with app.app_context():
                farm_report_service.generate(user_id)
        except Exception:
            app.logger.exception("Farm report generation failed for user %s", user_id)
        finally:
            with _report_lock:
                _report_running.discard(user_id)

    threading.Thread(target=_bg, daemon=False).start()
    return jsonify({"status": "generating"}), 202
