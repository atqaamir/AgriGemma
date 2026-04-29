from flask import Blueprint, request, jsonify, render_template
from marshmallow import ValidationError

from app.services.domain_service.task_service import TaskService
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
    tasks = list(TaskService.get_all_tasks())

    result = {
        "task_cards": task_card_schema.dump(tasks),
        "total_tasks": len(tasks),
        "pending_tasks_count": sum(1 for t in tasks if not t.completed),
        "completed_tasks_count": sum(1 for t in tasks if t.completed),
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


@tasks_bp.route("/tasks/<int:user_id>/critical-alert", methods=["GET"])
def get_critical_alert_for_user(user_id):
    
    print("Fetching critical alert for user ID:", user_id)

    
    return {
            "alert_title": "Extended Dry Spell Forecast",
            "alert_detail": "Data indicates 14 days of zero precipitation and 35°C peaks. Immediate irrigation adjustments required for the North and East quadrants.",
            "recommended_action": "Adjust Irrigation",
            "recommendation_confidence": 0.95,
        }
   

    service_= TaskService()
    alert = service_.get_critical_alert_for_user(user_id)
    return jsonify(alert), 200


@tasks_bp.route("/tasks/<int:user_id>/notifications", methods=["GET"])
def get_notifications_for_user(user_id):
    print("Fetching notifications for user ID:", user_id)
    notifications = [
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Irrigate field' is due in 2 hours", "type": "warning"},
        {"message": "Task 'Apply fertilizer' is overdue by 2 days", "type": "danger"},
        {"message": "Task 'Check drainage' is due in 1 day", "type": "reminder"},
        {"message": "New farming policy has been introduced by local govt", "type": "info"},
        {"message": "Crop Harvest is complete", "type": "info"},
        {"message": "Task 'Monitor crop health' is due in 1 week", "type": "reminder"},
    ]
    return jsonify({"notifications": notifications}), 200
