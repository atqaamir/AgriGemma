from flask import Blueprint, jsonify

crops_bp = Blueprint("crops", __name__)


@crops_bp.route("/", methods=["GET"])
def get_crops():
    return jsonify({
        "crops": [
            {
                "id": 1,
                "name": "Wheat",
                "field_name": "North Field",
                "growth_stage": "Flowering",
                "health_status": "Warning"
            },
            {
                "id": 2,
                "name": "Rice",
                "field_name": "South Field",
                "growth_stage": "Vegetative",
                "health_status": "Good"
            }
        ]
    }), 200