from flask import Blueprint, jsonify

fields_bp = Blueprint("fields", __name__)


@fields_bp.route("/", methods=["GET"])
def get_fields():
    return jsonify({
        "fields": [
            {
                "id": 1,
                "name": "North Field",
                "size_acres": 4.5,
                "crop": "Wheat"
            },
            {
                "id": 2,
                "name": "South Field",
                "size_acres": 3.0,
                "crop": "Rice"
            }
        ]
    }), 200