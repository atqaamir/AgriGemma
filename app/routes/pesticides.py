from flask import Blueprint, jsonify, request

from app.services.pesticide_service import (
    get_all_pesticides,
    get_pesticides_by_crop,
    get_pesticides_by_target_pest,
    recommend_pesticides,
    log_pesticide_use,
)

pesticides_bp = Blueprint("pesticides", __name__)


@pesticides_bp.route("/", methods=["GET"])
def list_pesticides():
    crop_type = request.args.get("crop_type")
    target_pest = request.args.get("target_pest")

    if crop_type and target_pest:
        result = recommend_pesticides(crop_type=crop_type, target_pest=target_pest)
    elif crop_type:
        result = get_pesticides_by_crop(crop_type)
    elif target_pest:
        result = get_pesticides_by_target_pest(target_pest)
    else:
        result = get_all_pesticides()

    return jsonify({"pesticides": result}), 200


@pesticides_bp.route("/recommend", methods=["GET"])
def recommend():
    crop_type = request.args.get("crop_type")
    target_pest = request.args.get("target_pest")

    result = recommend_pesticides(crop_type=crop_type, target_pest=target_pest)
    return jsonify({"recommendations": result}), 200


@pesticides_bp.route("/use", methods=["POST"])
def create_pesticide_use():
    data = request.get_json() or {}

    field_id = data.get("field_id")
    pesticide_id = data.get("pesticide_id")
    dosage_used = data.get("dosage_used")
    notes = data.get("notes")

    if not field_id or not pesticide_id:
        return jsonify({
            "error": "field_id and pesticide_id are required"
        }), 400

    result = log_pesticide_use(
        field_id=field_id,
        pesticide_id=pesticide_id,
        dosage_used=dosage_used,
        notes=notes
    )

    return jsonify({
        "message": "Pesticide use logged successfully",
        "pesticide_use": result
    }), 201