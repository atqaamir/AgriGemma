import json
import threading
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, render_template, current_app
from marshmallow import ValidationError

from app.agents.coordinator_agent import CoordinatorAgent
from app.extensions import db
from app.models.task_intelligence_summary import TaskIntelligenceSummary
from app.services.domain_service.task_service import TaskService
from app.schemas.task_schema import (
    TaskCardSchema,
    TaskDetailSchema,
    CreateTaskSchema,
    UpdateTaskSchema,
)
from app.schemas.intelligence_schema import TaskIntelligenceSchema

tasks_bp = Blueprint("tasks_bp", __name__)

task_card_schema = TaskCardSchema(many=True)
task_detail_schema = TaskDetailSchema()
task_create_schema = CreateTaskSchema()
task_update_schema = UpdateTaskSchema()
intelligence_schema = TaskIntelligenceSchema()

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


# ── AI Intelligence ───────────────────────────────────────────────────────────

@tasks_bp.route("/intelligence", methods=["GET"])
def get_task_intelligence():
    user_id = request.args.get("user_id", USER_ID, type=int)
    result = _coordinator.generate_task_intelligence(user_id)
    return jsonify(intelligence_schema.dump(result)), 200


@tasks_bp.route("/intelligence/stored", methods=["GET"])
def get_stored_intelligence():
    """Return the latest DB-cached intelligence — no AI call, instant."""
    user_id = request.args.get("user_id", USER_ID, type=int)
    row = (
        TaskIntelligenceSummary.query
        .filter_by(user_id=user_id)
        .order_by(TaskIntelligenceSummary.generated_at.desc())
        .first()
    )
    if not row:
        return jsonify(None), 200
    data = json.loads(row.data)
    data["generated_at"] = row.generated_at.isoformat()
    data["is_fallback"]  = row.is_fallback
    return jsonify(data), 200


@tasks_bp.route("/intelligence/generate", methods=["POST"])
def generate_and_store_intelligence():
    """Fire AI generation in background — returns immediately so navigation doesn't cancel it."""
    user_id = request.args.get("user_id", USER_ID, type=int)
    app = current_app._get_current_object()

    def _bg():
        with app.app_context():
            result = _coordinator.generate_task_intelligence(user_id)
            row = TaskIntelligenceSummary(
                user_id      = user_id,
                data         = json.dumps(intelligence_schema.dump(result)),
                is_fallback  = result.get("is_fallback", False),
                generated_at = datetime.now(timezone.utc),
            )
            db.session.add(row)
            db.session.commit()

    threading.Thread(target=_bg, daemon=False).start()
    return jsonify({"status": "generating"}), 202


# ── Task collection ───────────────────────────────────────────────────────────

@tasks_bp.route("/<int:user_id>/tasks", methods=["GET"])
def get_tasks_by_user(user_id):
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
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
