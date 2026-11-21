import threading

from flask import Blueprint, request, jsonify, render_template, current_app
from marshmallow import ValidationError

from app.agents.coordinator_agent import CoordinatorAgent
from app.services.domain_service.task_service import TaskService
from app.schemas.task_schema import (
    TaskCardSchema,
    TaskDetailSchema,
    CreateTaskSchema,
    UpdateTaskSchema,
)
from app.utils import clock

tasks_bp = Blueprint("tasks_bp", __name__)

task_card_schema = TaskCardSchema(many=True)
task_detail_schema = TaskDetailSchema()
task_create_schema = CreateTaskSchema()
task_update_schema = UpdateTaskSchema()

_coordinator = CoordinatorAgent()

USER_ID = 1  # TODO: replace with auth session user_id


# ── Page ─────────────────────────────────────────────────────────────────────

@tasks_bp.route("/", methods=["GET"])
def tasks_page():
    return render_template("tasks.html")


@tasks_bp.route("/tasks/lookup", methods=["GET"])
def get_task_lookup():
    from app.models.Lookup.task_lookup import TASK_TYPE_BY_CATEGORY
    return jsonify(TASK_TYPE_BY_CATEGORY), 200


# ── Task insights (one AI call on the "Task insights" button) ──────────────────

_insights_running: set[int] = set()
_insights_lock = threading.Lock()


@tasks_bp.route("/insights", methods=["GET"])
def get_task_insights():
    """Latest stored task insights + whether the farm changed since. No AI call."""
    from app.services import insight_report_service as reports
    user_id = request.args.get("user_id", USER_ID, type=int)
    data = reports.payload(user_id, "task_insights")
    with _insights_lock:
        running = user_id in _insights_running
    return jsonify({"report": data, "generating": running}), 200


@tasks_bp.route("/recommended-order", methods=["GET"])
def get_recommended_order():
    """The to-do list's "Recommended order": stored task insights when fresh, else the rules.
    No AI call."""
    from app.services import task_insights_service
    user_id = request.args.get("user_id", USER_ID, type=int)
    return jsonify(task_insights_service.recommended_order(user_id)), 200


@tasks_bp.route("/insights/generate", methods=["POST"])
def generate_task_insights():
    """Run the one AI call in the background (navigation doesn't cancel it); poll GET /insights."""
    from app.services import task_insights_service
    user_id = request.args.get("user_id", USER_ID, type=int)
    with _insights_lock:
        if user_id in _insights_running:
            return jsonify({"status": "already generating"}), 202
        _insights_running.add(user_id)
    app = current_app._get_current_object()

    def _bg():
        try:
            with app.app_context():
                task_insights_service.generate(user_id)
        except Exception:
            current_logger = app.logger
            current_logger.exception("Task insights generation failed for user %s", user_id)
        finally:
            with _insights_lock:
                _insights_running.discard(user_id)

    threading.Thread(target=_bg, daemon=False).start()
    return jsonify({"status": "generating"}), 202


@tasks_bp.route("/<int:user_id>/upcoming-harvest", methods=["GET"])
def get_upcoming_harvest(user_id):
    """Effective harvest dates from the plan (Upcoming Harvest card). Empty list → card hidden."""
    from app.services.plan_override_service import PlanOverrideService
    crops = PlanOverrideService.upcoming_harvests(user_id)
    dated = [c["harvest"] for c in crops if c["harvest"]]      # decision pending / skipped: no date
    return jsonify({"crops": crops,
                    "earliest": dated[0] if dated else None,
                    "latest": dated[-1] if dated else None}), 200


# ── Task collection ───────────────────────────────────────────────────────────

@tasks_bp.route("/<int:user_id>/tasks", methods=["GET"])
def get_tasks_by_user(user_id):
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 500)   # "all tasks" view asks for 500
    status = request.args.get("status", "all")
    search = request.args.get("search", "").strip()
    priority = request.args.get("priority")

    paginated = TaskService.get_tasks_by_user_paginated(user_id, page, per_page, status, search, priority)

    return jsonify({
        "task_cards": task_card_schema.dump(paginated.items),
        "total": paginated.total,
        "pending_count": TaskService.count_pending_by_user(user_id),
        "completed_count": TaskService.count_completed_by_user(user_id),
        "page": paginated.page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
    }), 200


@tasks_bp.route("/<int:user_id>/tasks/pending", methods=["GET"])
def get_pending_tasks_by_user(user_id):
    tasks = TaskService.get_pending_tasks_by_user(user_id)
    return jsonify({
        "task_cards": task_card_schema.dump(tasks),
        "count": len(tasks),
    }), 200


@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status", "all")
    search = request.args.get("search", "").strip()
    priority = request.args.get("priority")

    paginated = TaskService.get_tasks_paginated(page, per_page, status, search, priority)

    return jsonify({
        "task_cards": task_card_schema.dump(paginated.items),
        "total": paginated.total,
        "pending_count": TaskService.count_pending(),
        "completed_count": TaskService.count_completed(),
        "page": paginated.page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
    }), 200


@tasks_bp.route("/tasks/pending", methods=["GET"])
def get_pending_tasks():
    tasks = TaskService.get_pending_tasks()
    return jsonify({
        "task_cards": task_card_schema.dump(tasks),
        "count": len(tasks),
    }), 200


# ── Single task ───────────────────────────────────────────────────────────────

@tasks_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = TaskService.get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task_detail_schema.dump(task)), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    try:
        valid_data = task_create_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    task = TaskService.create_task(valid_data)
    return jsonify(task_detail_schema.dump(task)), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = TaskService.get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json() or {}
    try:
        valid_data = task_update_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    updated = TaskService.update_task(task_id, valid_data)
    return jsonify(task_detail_schema.dump(updated)), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = TaskService.get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    TaskService.delete_task(task_id)
    return jsonify({"message": "Task deleted successfully"}), 200


# ── Weather Change Simulator ──────────────────────────────────────────────────

@tasks_bp.route("/<int:user_id>/run-refresh-data", methods=["POST"])
def run_refresh_data(user_id):
    from app.utils import demo_flags
    if not demo_flags.admin_enabled():
        # Wipes and reseeds the whole database: never on the live demo.
        return jsonify({"error": "Refresh Data is disabled on the live demo."}), 403
    try:
        import Test_Runs.seed_data as seed_data
        import Test_Runs.populate_seasonal_plan as populate_seasonal_plan
        import Test_Runs.populate_weekly_plan as populate_weekly_plan

        seed_data.run()
        populate_seasonal_plan.run()
        populate_weekly_plan.run()

        return jsonify({"message": "Data refreshed successfully."}), 200
    except Exception as exc:
        current_app.logger.exception("run_refresh_data failed for user %s", user_id)
        return jsonify({"error": str(exc)}), 500


@tasks_bp.route("/<int:user_id>/demo-cooldowns", methods=["GET"])
def demo_cooldowns(user_id):
    """Seconds left on the simulator (per user) and Reset demo (global) cooldowns, so the
    page can show a countdown that survives a reload. Read-only."""
    from app.utils import demo_flags
    return jsonify({"simulator": demo_flags.simulator_remaining(user_id),
                    "reset": demo_flags.reset_remaining()}), 200


@tasks_bp.route("/<int:user_id>/reset-demo", methods=["POST"])
def reset_demo(user_id):
    """Back to the fresh-start state (reseed + calm startup forecast). Allowed on the live
    demo (only demo data), unlike Refresh Data; one reset per 60 s for the whole app."""
    from app.utils import demo_flags
    wait = demo_flags.reset_wait_seconds()
    if wait:
        resp = jsonify({"error": f"The demo was just reset – try again in {wait} s", "retry_after": wait})
        resp.headers["Retry-After"] = str(wait)
        return resp, 429
    try:
        from app.services import deferred_ai_service as deferred
        from app.services.demo_reset_service import reset_demo as _reset
        deferred.invalidate_all()          # background AI work of earlier runs is dropped
        _reset()
        d = clock.today()
        return jsonify({"message": f"Demo reset to the starting state ({d.day} {d:%B}, no forecast change)."}), 200
    except Exception as exc:
        from app.extensions import db
        db.session.rollback()
        current_app.logger.exception("reset_demo failed (requested by user %s)", user_id)
        return jsonify({"error": str(exc)}), 500


@tasks_bp.route("/<int:user_id>/run-weather-simulator", methods=["POST"])
def run_weather_simulator(user_id):
    from app.utils import demo_flags
    from app.services import demo_scenario_service as scenarios
    key = (request.get_json(silent=True) or {}).get("scenario") or scenarios.DEFAULT
    if key not in scenarios.SCENARIOS:   # before the cooldown: a bad request does not use it up
        return jsonify({"error": f"Unknown scenario: {key}"}), 400
    wait = demo_flags.simulator_wait_seconds(user_id)
    if wait:
        resp = jsonify({"error": f"Simulator just ran – try again in {wait} s", "retry_after": wait})
        resp.headers["Retry-After"] = str(wait)
        return resp, 429
    try:
        from app.repositories.weather_repository import WeatherRepository
        from app.services.domain_service.user_service import UserService
        from Test_Runs.seed_data import seed_demo_weather
        today = clock.today()

        # Self-healing demo weather: if the app has been up longer than the seeded
        # 7-day window, top up baseline + forecast starting today.
        location = UserService.get_user_location(user_id)
        if location and not WeatherRepository.get_by_region_and_date(location, today):
            seed_demo_weather(start=today)

        # The scenario writes the 7-day forecast (baseline + its days); the full daily
        # update (rolls the plan to today..today+6) then reacts to it through the rules.
        # The response does not wait for the AI: notifications get their rule-based text,
        # the AI texts follow in the background (a newer run makes them stale).
        from app.models.notification import Notification
        from app.services import deferred_ai_service as deferred
        last = Notification.query.order_by(Notification.id.desc()).first()
        first_id = (last.id + 1) if last else 1
        with deferred.foreground(user_id) as run:
            scenarios.apply(user_id, key)
            result = _coordinator.daily_update(user_id=user_id, as_of_date=today, defer_ai=True)
        deferred.start(current_app._get_current_object(), user_id, run, first_id)

        return jsonify({
            "message": f"Simulation complete — {result.get('message', 'done')}",
            "scenario": key,
            "scenario_label": scenarios.SCENARIOS[key]["label"],
            "banner": scenarios.banner(user_id),
            "change_status": result.get("change_status"),
            "execution_status": result.get("execution_status"),
        }), 200
    except Exception as exc:
        current_app.logger.exception("weather_simulator failed for user %s", user_id)
        return jsonify({"error": str(exc)}), 500

# ── Decision needed: the farmer's answer (stage 2) ─────────────────────────────────────
def _decision_action(user_id, action):
    """Run a decision action, then the AI texts in the background (as after a simulator run)."""
    from app.models.notification import Notification
    from app.services import decision_actions_service as decisions
    from app.services import deferred_ai_service as deferred
    try:
        last = Notification.query.order_by(Notification.id.desc()).first()
        first_id = (last.id + 1) if last else 1
        with deferred.foreground(user_id) as run:
            result = action()
        deferred.start(current_app._get_current_object(), user_id, run, first_id)
        return jsonify(result), 200
    except decisions.DecisionError as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception as exc:
        current_app.logger.exception("decision action failed for user %s", user_id)
        return jsonify({"error": str(exc)}), 500


@tasks_bp.route("/<int:user_id>/decision/<int:task_id>/sow-anyway", methods=["POST"])
def decision_sow_anyway(user_id, task_id):
    from app.services import decision_actions_service as decisions
    return _decision_action(user_id, lambda: decisions.sow_anyway(user_id, task_id))


@tasks_bp.route("/<int:user_id>/decision/<int:task_id>/skip-season", methods=["POST"])
def decision_skip_season(user_id, task_id):
    from app.services import decision_actions_service as decisions
    return _decision_action(user_id, lambda: decisions.skip_season(user_id, task_id))


@tasks_bp.route("/<int:user_id>/seasonal-entry/<int:entry_id>/undo-decision", methods=["POST"])
def decision_undo(user_id, entry_id):
    from app.services import decision_actions_service as decisions
    return _decision_action(user_id, lambda: decisions.undo(user_id, entry_id))
