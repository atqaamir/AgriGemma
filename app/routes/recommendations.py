"""Recommendations API routes."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields

from app.services.recommendation_service import RecommendationService

recommendations_bp = Blueprint("recommendations", __name__)


class RecommendationRequestSchema(Schema):
    weather = fields.Dict(required=True)
    soil = fields.Dict(required=True)
    crop = fields.Dict(required=True)


recommendation_request_schema = RecommendationRequestSchema()


@recommendations_bp.route("/generate", methods=["POST"])
def generate_recommendation():
    """Generate AI-powered farming recommendation."""
    data = request.get_json() or {}
    
    try:
        valid_data = recommendation_request_schema.load(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    result = RecommendationService.generate_recommendation(
        weather=valid_data["weather"],
        soil=valid_data["soil"],
        crop=valid_data["crop"],
    )
    
    if result["success"]:
        return jsonify(result), 200
    else:
        return jsonify({"error": result["error"]}), 500


@recommendations_bp.route("/task-alerts", methods=["POST"])
def generate_task_alerts():
    """Generate urgent task alerts."""
    data = request.get_json() or {}
    
    try:
        valid_data = recommendation_request_schema.load(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    result = RecommendationService.generate_task_alerts(
        weather=valid_data["weather"],
        soil=valid_data["soil"],
        crop=valid_data["crop"],
    )
    
    if result["success"]:
        return jsonify(result), 200
    else:
        return jsonify({"error": result["error"]}), 500