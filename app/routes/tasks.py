from flask import Blueprint, jsonify

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/", methods=["GET"])
def get_tasks():
    return jsonify({
        "tasks": [
            {
                "title": "Irrigate the field",
                "priority": "high",
                "due": "today",
                "status": "pending"
            },
            {
                "title": "Inspect crop for pests",
                "priority": "medium",
                "due": "today",
                "status": "pending"
            }
        ],
        "alerts": [
            {
                "message": "Heatwave risk in the next 24 hours",
                "level": "high",
                "type": "weather"
            }
        ]
    }), 200