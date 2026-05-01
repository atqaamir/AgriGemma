from flask import Blueprint, request, jsonify, render_template, current_app
from marshmallow import ValidationError

from app.agents.coordinator_agent import CoordinatorAgent
from app.services.domain_service.task_service import TaskService
from app.services.task_event_service import TaskEventService
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


# ── AI Intelligence ───────────────────────────────────────────────────────────

@tasks_bp.route("/intelligence", methods=["GET"])
def get_task_intelligence():
    user_id = request.args.get("user_id", USER_ID, type=int)
    result = _coordinator.generate_task_intelligence(user_id)
    return jsonify(intelligence_schema.dump(result)), 200


# ── Task collection ───────────────────────────────────────────────────────────

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
    TaskEventService.on_task_change(USER_ID, current_app._get_current_object())
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
    TaskEventService.on_task_change(USER_ID, current_app._get_current_object())
    return jsonify(task_detail_schema.dump(updated)), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = TaskService.get_task_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    TaskService.delete_task(task_id)
    TaskEventService.on_task_change(USER_ID, current_app._get_current_object())
    return jsonify({"message": "Task deleted successfully"}), 200
