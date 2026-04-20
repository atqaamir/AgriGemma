from flask import Blueprint, request, jsonify, render_template
from marshmallow import ValidationError

from app.services.task_service import TaskService
from app.schemas.task_schema import (
    TaskCardSchema,
    TaskDetailSchema,
    CreateTaskSchema,
    UpdateTaskSchema,
)

tasks_bp = Blueprint("tasks_bp", __name__)

task_card_schema = TaskCardSchema(many=True)
task_detail_schema = TaskDetailSchema()
task_create_schema = CreateTaskSchema()
task_update_schema = UpdateTaskSchema()


@tasks_bp.route("/", methods=["GET"])
def tasks_page():
    return render_template("tasks.html")


@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = TaskService.get_all_tasks()

    result = {
        "task_cards": task_card_schema.dump(tasks),
        "total_tasks": len(tasks),
        "pending_tasks_count": len([task for task in tasks if not task.completed]),
        "completed_tasks_count": len([task for task in tasks if task.completed]),
    }

    return jsonify(result), 200


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

    updated_task = TaskService.update_task(task_id, valid_data)
    return jsonify(task_detail_schema.dump(updated_task)), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = TaskService.get_task_by_id(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    TaskService.delete_task(task_id)
    return jsonify({"message": "Task deleted successfully"}), 200